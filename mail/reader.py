import imaplib
import email
import re
from email.header import decode_header, make_header
from email.utils import parseaddr
from datetime import datetime

class MailReader:
    def __init__(self, auth_manager, storage_manager, config, save_config_callback):
        self.auth_manager = auth_manager
        self.storage_manager = storage_manager
        self.config = config
        self.save_config_callback = save_config_callback

    def fetch_emails(self, account, auth_password, limit=10, search_criteria=None):
        account_name = account.get("friendly_name")
        sync_info = self.storage_manager.get_last_sync_info(account_name)
        is_offline = False
        newly_fetched_emails = []
        
        # Determine sync range
        # Default to a larger fetch_limit to ensure we capture most recent emails and detect deletions
        # If limit is small (like 10), we still fetch more UIDs to detect remote deletions effectively.
        fetch_limit = max(limit, 100) 
        
        # Check if we need to sync all emails (e.g. first run)
        sync_all = account.get("sync_all_on_next_run", False)
        if sync_all:
            fetch_limit = 2000 # Larger limit for "all" sync

        try:
            # Before fetching new emails, process any pending actions (like deletions)
            self.sync_pending_actions(account, auth_password)
            
            auth = self.auth_manager.decrypt_account_auth(account, auth_password)
            mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
            
            # ... (authentication logic) ...
            if account['login_method'] == "Account/Password":
                mail.login(auth['username'], auth['password'])
            else:
                user = auth.get("username")
                token = auth.get("access_token")
                try:
                    auth_string = f"user={user}\x01auth=Bearer {token}\x01\x01"
                    mail.authenticate('XOAUTH2', lambda x: auth_string)
                except imaplib.IMAP4.error:
                    new_token = self.auth_manager.refresh_oauth2_token(account, auth, auth_password, self.config)
                    if new_token:
                        self.save_config_callback()
                        mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
                        auth_string = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                        mail.authenticate('XOAUTH2', lambda x: auth_string)
                    else:
                        raise Exception("Authentication failed.")

            mail.select("INBOX")
            
            # 1. Fetch ALL UIDs from server to detect deletions
            res, data = mail.uid('search', None, "ALL")
            if res == "OK":
                uids_raw = data[0].split()
                server_uids = {uid.decode() for uid in uids_raw}
                
                # 2. Sync deletions (Remote -> Local)
                cached_uids = self.storage_manager.get_all_cached_uids(account_name)
                cached_uids_set = set(cached_uids)
                for cached_uid in cached_uids:
                    if cached_uid not in server_uids:
                        self.storage_manager.delete_email_from_cache(account_name, cached_uid)
                
                # 3. Identify truly NEW emails that are not in cache
                # We only fetch metadata for these
                new_uids_to_fetch = [uid for uid in uids_raw if uid.decode() not in cached_uids_set]
                
                # If we have too many new emails, we might still want to respect some limit
                # but for now, let's fetch metadata for all new ones up to fetch_limit
                if len(new_uids_to_fetch) > fetch_limit:
                    new_uids_to_fetch = new_uids_to_fetch[-fetch_limit:]
                
                # 4. Performance optimization: Sync Flags (Seen/Unseen) for existing emails in the current view
                # We check flags for the 'limit' most recent emails
                view_uids = uids_raw[-limit:] if len(uids_raw) > limit else uids_raw
                view_uids_str = b",".join(view_uids)
                if view_uids_str:
                    res, flag_data = mail.uid('fetch', view_uids_str.decode(), '(FLAGS)')
                    if res == "OK" and flag_data:
                        for item in flag_data:
                            if isinstance(item, tuple):
                                content = item[0].decode()
                                uid_match = re.search(r'UID (\d+)', content)
                                if uid_match:
                                    f_uid = uid_match.group(1)
                                    is_seen = '\\Seen' in content
                                    self.storage_manager.update_email_seen_status(account_name, f_uid, is_seen)

                # 5. Fetch Metadata for NEW emails
                fetched_emails = []
                if new_uids_to_fetch:
                    # Fetch in reversed order (newest first)
                    for uid in reversed(new_uids_to_fetch):
                        uid_str = uid.decode()
                        res, msg_data = mail.uid('fetch', uid, '(RFC822.SIZE BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
                        if res == "OK":
                            raw_msg = msg_data[0][1]
                            msg = email.message_from_bytes(raw_msg)
                            
                            # (Header decoding logic remains same...)
                            try:
                                subject_header = msg.get("Subject")
                                subject = str(make_header(decode_header(subject_header))) if subject_header else "No Subject"
                            except Exception:
                                subject = msg.get("Subject", "No Subject")
                            
                            try:
                                from_header_raw = msg.get("From", "Unknown")
                                from_header = str(make_header(decode_header(from_header_raw)))
                            except Exception:
                                from_header = msg.get("From", "Unknown")
                            
                            name, email_addr = parseaddr(from_header)
                            sender_name = name or (from_header.split("<")[0].strip() if "<" in from_header else from_header)
                            sender_name = sender_name.replace('"', '').replace("'", "").strip()
                            if not sender_name or sender_name == email_addr:
                                sender_name = email_addr or from_header
                            
                            fetched_emails.append({
                                "id": uid_str,
                                "from": sender_name,
                                "from_email": email_addr,
                                "subject": subject,
                                "date": msg.get("Date"),
                                "seen": '\\Seen' in str(msg_data[0][0])
                            })
                
                if fetched_emails:
                    newly_added_uids = self.storage_manager.save_emails_to_cache(account_name, fetched_emails, auth_password)
                    newly_fetched_emails = [e for e in fetched_emails if e["id"] in newly_added_uids]
                
                # Update sync status
                new_last_uid = uids_raw[-1].decode() if uids_raw else sync_info.get("uid", "0")
                self.storage_manager.update_sync_info(account_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), new_last_uid)
                sync_info = self.storage_manager.get_last_sync_info(account_name)

                if sync_all:
                    account["sync_all_on_next_run"] = False
                    self.save_config_callback()

            mail.close()
            mail.logout()
            
        except Exception as e:
            is_offline = True
            sync_error = str(e)
            return self.storage_manager.get_emails_from_cache(account_name, limit, search_criteria, auth_password), {"last_sync": sync_info.get("time"), "is_offline": is_offline, "error": sync_error, "new_emails": []}

        email_list = self.storage_manager.get_emails_from_cache(account_name, limit, search_criteria, auth_password)
        return email_list, {"last_sync": sync_info.get("time"), "is_offline": is_offline, "new_emails": newly_fetched_emails}

    def read_email(self, account, auth_password, email_id):
        account_name = account.get("friendly_name")
        
        # 1. Check cache first
        content_type, content = self.storage_manager.get_email_content(account_name, email_id, auth_password)
        if content:
            if content_type == "html_only":
                return {"type": "html_only", "html": content}
            return content

        # 2. If not in cache, fetch from server
        try:
            auth = self.auth_manager.decrypt_account_auth(account, auth_password)
            mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
            
            if account['login_method'] == "Account/Password":
                mail.login(auth['username'], auth['password'])
            else:
                user = auth.get("username")
                token = auth.get("access_token")
                try:
                    auth_string = f"user={user}\x01auth=Bearer {token}\x01\x01"
                    mail.authenticate('XOAUTH2', lambda x: auth_string)
                except imaplib.IMAP4.error:
                    new_token = self.auth_manager.refresh_oauth2_token(account, auth, auth_password, self.config)
                    if new_token:
                        self.save_config_callback()
                        mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
                        auth_string = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                        mail.authenticate('XOAUTH2', lambda x: auth_string)
                    else:
                        raise Exception("Authentication failed.")

            mail.select("INBOX")
            # Mark as seen on server
            mail.uid('store', email_id, '+FLAGS', '\\Seen')
            # Fetch content
            res, msg_data = mail.uid('fetch', email_id, "(RFC822)")
            
            content = ""
            html_content = ""
            if res == "OK":
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        if msg.is_multipart():
                            for subpart in msg.walk():
                                c_type = subpart.get_content_type()
                                if c_type == "text/plain":
                                    charset = subpart.get_content_charset() or "utf-8"
                                    content = subpart.get_payload(decode=True).decode(charset, errors="replace")
                                elif c_type == "text/html":
                                    charset = subpart.get_content_charset() or "utf-8"
                                    html_content = subpart.get_payload(decode=True).decode(charset, errors="replace")
                        else:
                            c_type = msg.get_content_type()
                            charset = msg.get_content_charset() or "utf-8"
                            if c_type == "text/plain":
                                content = msg.get_payload(decode=True).decode(charset, errors="replace")
                            elif c_type == "text/html":
                                html_content = msg.get_payload(decode=True).decode(charset, errors="replace")
            
            final_content = content or html_content
            final_type = "text/plain" if content else "html_only"
            
            # 3. Save to cache
            if final_content:
                self.storage_manager.update_email_content(account_name, email_id, final_type, final_content, auth_password)

            mail.close()
            mail.logout()
            
            if final_type == "html_only":
                return {"type": "html_only", "html": final_content}
            return final_content

        except Exception as e:
            return f"Error: {e}"

    def delete_email(self, account, auth_password, email_id):
        """
        Delete an email by UID from both remote server and local cache.
        If network fails, records a pending action for later synchronization.
        """
        account_name = account.get("name")
        mail = None
        try:
            # 1. Try to delete from remote server
            mail = self._connect_imap(account, auth_password)
            mail.select("INBOX")
            
            # Store the deletion in IMAP
            mail.uid('STORE', email_id, '+FLAGS', '(\\Deleted)')
            mail.expunge()
            
            # 2. If remote success, delete from local cache
            self.storage_manager.delete_email_from_cache(account_name, email_id)
            
            mail.close()
            mail.logout()
            return True, "Email deleted successfully from server and local cache."
            
        except Exception as e:
            # 3. If remote fails (network issue), record as pending action
            print(f"⚠️ Network issue during deletion: {e}. Recording for later sync.")
            self.storage_manager.add_pending_action(account_name, 'delete', email_id)
            # Also remove from local cache to provide immediate feedback to user
            self.storage_manager.delete_email_from_cache(account_name, email_id)
            
            if mail:
                try:
                    mail.logout()
                except:
                    pass
            return False, f"Network issue: Deletion scheduled for next sync. Local cache updated."

    def sync_pending_actions(self, account, auth_password):
        """
        Process pending actions (like deletions) that failed previously.
        """
        account_name = account.get("name")
        pending_actions = self.storage_manager.get_pending_actions(account_name)
        
        if not pending_actions:
            return
            
        mail = None
        processed_ids = []
        try:
            mail = self._connect_imap(account, auth_password)
            mail.select("INBOX")
            
            for action_id, action_type, uid in pending_actions:
                if action_type == 'delete':
                    try:
                        # Try to delete from remote
                        mail.uid('STORE', uid, '+FLAGS', '(\\Deleted)')
                        processed_ids.append(action_id)
                    except Exception as e:
                        print(f"Failed to process pending deletion for UID {uid}: {e}")
            
            if processed_ids:
                mail.expunge()
                # Remove successfully processed actions from DB
                for action_id in processed_ids:
                    self.storage_manager.remove_pending_action(action_id)
                print(f"✅ Processed {len(processed_ids)} pending actions for {account_name}.")
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            print(f"⚠️ Failed to sync pending actions for {account_name}: {e}")
            if mail:
                try:
                    mail.logout()
                except:
                    pass
