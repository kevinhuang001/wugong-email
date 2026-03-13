import imaplib
import email
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
        
        # Check if we need to sync all emails
        sync_all = account.get("sync_all_on_next_run", False)
        if sync_all:
            # If sync_all is requested, we'll fetch all UIDs and sync them
            # For performance, we might still want a reasonable upper limit or just do it in batches
            # but for now, let's just use a very large limit.
            fetch_limit = 1000 # Reasonable "all" for first sync
        else:
            fetch_limit = limit

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
            
            # Fetch the latest UIDs to ensure metadata is up-to-date in cache
            res, data = mail.uid('search', None, "ALL")
            if res == "OK":
                uids = data[0].split()
                # Get the last 'fetch_limit' UIDs
                latest_uids = uids[-fetch_limit:] if len(uids) > fetch_limit else uids
                
                fetched_emails = []
                for uid in reversed(latest_uids):
                    res, msg_data = mail.uid('fetch', uid, '(RFC822.SIZE BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
                    if res == "OK":
                        raw_msg = msg_data[0][1]
                        msg = email.message_from_bytes(raw_msg)
                        
                        # Improved header decoding for Subject
                        try:
                            # Handle potential None or empty Subject
                            subject_header = msg.get("Subject")
                            if subject_header:
                                subject = str(make_header(decode_header(subject_header)))
                            else:
                                subject = "No Subject"
                        except Exception:
                            subject = msg.get("Subject", "No Subject")
                        
                        # Improved header decoding and address parsing for From
                        try:
                            from_header_raw = msg.get("From", "Unknown")
                            from_header = str(make_header(decode_header(from_header_raw)))
                        except Exception:
                            from_header = msg.get("From", "Unknown")
                        
                        name, email_addr = parseaddr(from_header)
                        
                        # Clean up the name and email
                        # 1. If we have a name from parseaddr, use it. Otherwise use the part before < if present.
                        sender_name = name
                        if not sender_name:
                            if "<" in from_header:
                                sender_name = from_header.split("<")[0].strip()
                            else:
                                sender_name = from_header
                        
                        # 2. Final cleaning: remove quotes and extra spaces
                        sender_name = sender_name.replace('"', '').replace("'", "").strip()
                        
                        # 3. If it's still just the email or empty, fallback
                        if not sender_name or sender_name == email_addr:
                            sender_name = email_addr or from_header
                        
                        fetched_emails.append({
                            "id": uid.decode(),
                            "from": sender_name,
                            "from_email": email_addr,
                            "subject": subject,
                            "date": msg.get("Date"),
                            "seen": False # New emails are assumed unread for now
                        })
                
                if fetched_emails:
                    new_uids = self.storage_manager.save_emails_to_cache(account_name, fetched_emails, auth_password)
                    # Get the actual email objects for newly added UIDs
                    newly_fetched_emails = [e for e in fetched_emails if e["id"] in new_uids]
                
                # Update sync status
                new_last_uid = uids[-1].decode() if uids else sync_info.get("uid", "0")
                self.storage_manager.update_sync_info(account_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), new_last_uid)
                sync_info = self.storage_manager.get_last_sync_info(account_name)

                # Clear sync_all flag if it was set
                if sync_all:
                    account["sync_all_on_next_run"] = False
                    self.save_config_callback()

            mail.close()
            mail.logout()
            
        except Exception as e:
            # print(f"DEBUG: Sync failed for {account_name}: {e}") # Debugging
            is_offline = True
            sync_error = str(e)
            return self.storage_manager.get_emails_from_cache(account_name, limit, search_criteria, auth_password), {"last_sync": sync_info.get("time"), "is_offline": is_offline, "error": sync_error, "new_emails": []}

        # Always return from cache (which now includes newly fetched emails)
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
