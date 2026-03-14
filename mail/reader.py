import imaplib
import email
from email.header import decode_header, make_header
from email.utils import parseaddr
from datetime import datetime
import re
import socket
import ssl

class MailReader:
    def __init__(self, auth_manager, storage_manager, config, save_config_callback):
        self.auth_manager = auth_manager
        self.storage_manager = storage_manager
        self.config = config
        self.save_config_callback = save_config_callback

    def _connect_imap(self, account, auth_password):
        """Helper to connect and authenticate to IMAP server based on configured TLS method."""
        imap_server = account['imap_server']
        imap_port = int(account['imap_port'])
        tls_method = account.get('imap_tls_method', 'SSL/TLS')
        
        if tls_method == "SSL/TLS":
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        elif tls_method == "STARTTLS":
            mail = imaplib.IMAP4(imap_server, imap_port)
            mail.starttls()
        else:
            mail = imaplib.IMAP4(imap_server, imap_port)
            
        auth = self.auth_manager.decrypt_account_auth(account, auth_password)
        
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
                    # Reconnect if token refreshed
                    if tls_method == "SSL/TLS":
                        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
                    elif tls_method == "STARTTLS":
                        mail = imaplib.IMAP4(imap_server, imap_port)
                        mail.starttls()
                    else:
                        mail = imaplib.IMAP4(imap_server, imap_port)
                    auth_string = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                    mail.authenticate('XOAUTH2', lambda x: auth_string)
                else:
                    raise Exception("Authentication failed.")
        return mail

    def fetch_emails(self, account, auth_password, limit=20, search_criteria=None, progress_callback=None, is_initial_sync=False, sync=True):
        """
        Original fetch_emails, now used primarily for 'sync' command.
        It processes pending actions, syncs deletions, fetches NEW emails, and updates sync time.
        """
        account_name = account.get("friendly_name")
        sync_info = self.storage_manager.get_last_sync_info(account_name)
        is_offline = False
        newly_fetched_emails = []
        
        if sync:
            try:
                # 1. Process pending actions (like deletions)
                self.sync_pending_actions(account, auth_password)
                
                mail = self._connect_imap(account, auth_password)

                mail.select("INBOX")
                
                # 2. Sync Logic (Incremental, Full, or Recent Limit)
                search_query_args = []
                if is_initial_sync:
                    search_query_args.append("ALL")
                else:
                    if search_criteria:
                        if search_criteria.get("keyword"):
                            search_query_args.extend(["OR", "SUBJECT", search_criteria["keyword"], "BODY", search_criteria["keyword"]])
                        if search_criteria.get("from"):
                            search_query_args.extend(["FROM", search_criteria["from"]])
                        if search_criteria.get("since"):
                            try:
                                since_val = search_criteria["since"]
                                if re.match(r'\d{1,2}-[A-Za-z]{3}-\d{4}', since_val):
                                    since_date = since_val
                                else:
                                    since_date = datetime.strptime(since_val, "%Y-%m-%d").strftime("%d-%b-%Y")
                                search_query_args.extend(["SINCE", since_date])
                            except: pass
                        if search_criteria.get("before"):
                            try:
                                before_val = search_criteria["before"]
                                if re.match(r'\d{1,2}-[A-Za-z]{3}-\d{4}', before_val):
                                    before_date = before_val
                                else:
                                    before_date = datetime.strptime(before_val, "%Y-%m-%d").strftime("%d-%b-%Y")
                                search_query_args.extend(["BEFORE", before_date])
                            except: pass
                    
                    if not search_query_args:
                        if limit == -1 or limit > 0:
                            search_query_args.append("ALL")
                        else:
                            last_sync_time = sync_info.get("time")
                            if last_sync_time and last_sync_time != "Never":
                                try:
                                    last_date = datetime.strptime(last_sync_time, "%Y-%m-%d %H:%M:%S").strftime("%d-%b-%Y")
                                    search_query_args.extend(["SINCE", last_date])
                                except:
                                    search_query_args.append("ALL")
                            else:
                                search_query_args.append("ALL")

                # Helper to encode non-ASCII tokens to bytes (imaplib will send as literals)
                # but keep ASCII as strings (imaplib will send as quoted strings or atoms)
                def process_token(t):
                    if not isinstance(t, str): return t
                    try:
                        t.encode('ascii')
                        return t
                    except UnicodeEncodeError:
                        return t.encode('utf-8')

                # Strategy: Try ASCII first, if fails or contains non-ASCII, try UTF-8
                # If UTF-8 fails (BAD command), fallback to local and warn user
                try:
                    # 1. Try standard search (no charset specified, assumes ASCII)
                    # This is most compatible with older servers
                    res, data = mail.uid('search', None, *search_query_args)
                except (imaplib.IMAP4.error, UnicodeEncodeError, TypeError):
                    # If standard search fails due to non-ASCII or server error, try UTF-8
                    try:
                        final_args = [process_token(arg) for arg in search_query_args]
                        # Use search_query_args for charset to see if it makes a difference, 
                        # but some servers require the charset string.
                        res, data = mail.uid('search', "UTF-8", *final_args)
                    except (imaplib.IMAP4.error, TypeError) as e:
                        # Server doesn't support UTF-8 search or command is BAD
                        is_offline = True
                        sync_error = f"IMAP search failed (UTF-8 not supported?): {str(e)}"
                        # Close and fallback
                        try:
                            mail.logout()
                        except: pass
                        cached_emails = self.storage_manager.get_emails_from_cache(account_name, limit, search_criteria, auth_password)
                        return cached_emails, {"last_sync": sync_info.get("time"), "is_offline": is_offline, "error": sync_error, "new_emails": []}
                
                if res == "OK":
                    search_query_all = "ALL" in search_query_args and len(search_query_args) == 1
                    uids_raw = data[0].split()
                    server_uids = {uid.decode() for uid in uids_raw}
                    
                    # 3. Sync deletions (Remote -> Local) - only if we have full view (search ALL)
                    if search_query_all:
                        cached_uids = self.storage_manager.get_all_cached_uids(account_name)
                        for cached_uid in cached_uids:
                            if cached_uid not in server_uids:
                                self.storage_manager.delete_email_from_cache(account_name, cached_uid)
                    
                    # 4. Identify UIDs to process (sync)
                    if is_initial_sync:
                        init_limit = limit
                        if init_limit == -1:
                            uids_to_process = uids_raw
                        else:
                            uids_to_process = uids_raw[-init_limit:] if len(uids_raw) > init_limit else uids_raw
                    elif limit > 0 and not search_criteria:
                        # User specified a specific limit of recent emails for sync
                        uids_to_process = uids_raw[-limit:] if len(uids_raw) > limit else uids_raw
                    else:
                        # Incremental or other sync
                        uids_to_process = uids_raw
                    
                    if uids_to_process:
                        total_uids = len(uids_to_process)
                        uids_to_process_decoded = [uid.decode() for uid in uids_to_process]
                        
                        # Get cached statuses for comparison
                        cached_statuses = self.storage_manager.get_cached_statuses(account_name, uids_to_process_decoded)
                        
                        # Fetch current FLAGS for all UIDs to process in batches
                        server_statuses = {}
                        batch_size = 500
                        for i in range(0, len(uids_to_process), batch_size):
                            batch = uids_to_process[i:i + batch_size]
                            uids_str = ",".join([uid.decode() for uid in batch])
                            res, data = mail.uid('fetch', uids_str, '(FLAGS)')
                            if res == "OK":
                                for item in data:
                                    if isinstance(item, tuple):
                                        resp_text = item[0].decode()
                                        uid_match = re.search(r'UID (\d+)', resp_text)
                                        if uid_match:
                                            uid = uid_match.group(1)
                                            is_seen = '\\Seen' in resp_text
                                            server_statuses[uid] = is_seen

                        # Now iterate and sync (reversed for latest first)
                        for i, uid_bin in enumerate(reversed(uids_to_process)):
                            uid_str = uid_bin.decode()
                            server_seen = server_statuses.get(uid_str, False)
                            
                            if progress_callback:
                                msg = f"Syncing {i+1}/{total_uids}..."
                                progress_callback(i + 1, total_uids, msg)

                            if uid_str in cached_statuses:
                                # Email is in cache, check if status changed
                                if server_seen != cached_statuses[uid_str]:
                                    self.storage_manager.update_seen_status(account_name, uid_str, server_seen)
                            else:
                                # Email is NOT in cache, fetch full content
                                res, msg_data = mail.uid('fetch', uid_bin, '(RFC822)')
                                if res == "OK" and msg_data[0]:
                                    raw_msg = msg_data[0][1]
                                    msg = email.message_from_bytes(raw_msg)
                                    # Use the seen status we already fetched to avoid another fetch
                                    status_data = f"(FLAGS ({'\\Seen' if server_seen else ''}))"
                                    parsed = self._parse_email(uid_str, msg, status_data)
                                    newly_fetched_emails.append(parsed)
                                    
                                    # Save to cache immediately if needed, or batch it
                                    # For now we'll collect and save at the end as before
                        
                        if newly_fetched_emails:
                            self.storage_manager.save_emails_to_cache(account_name, newly_fetched_emails, auth_password)
                    
                    # 6. Update sync status
                    new_last_uid = uids_raw[-1].decode() if uids_raw else sync_info.get("uid", "0")
                    self.storage_manager.update_sync_info(account_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), new_last_uid)
                    sync_info = self.storage_manager.get_last_sync_info(account_name)

                mail.close()
                mail.logout()
                
            except socket.timeout as e:
                is_offline = True
                sync_error = f"Connection timeout: {str(e)}"
                cached_emails = self.storage_manager.get_emails_from_cache(account_name, limit, search_criteria, auth_password)
                return cached_emails, {"last_sync": sync_info.get("time"), "is_offline": is_offline, "error": sync_error, "new_emails": []}
            except Exception as e:
                # SSL, Protocol errors, or other bugs: re-raise directly, don't fallback to cache
                raise e

        # Final return from cache
        email_list = self.storage_manager.get_emails_from_cache(account_name, limit, search_criteria, auth_password)
        return email_list, {"last_sync": sync_info.get("time"), "is_offline": is_offline, "new_emails": newly_fetched_emails}

    def query_emails(self, account, auth_password, limit=20, search_criteria=None, progress_callback=None, local_only=False):
        """
        Pure query method for 'list' command.
        Prefers IMAP search, but doesn't do 'sync' (pending actions, deletion sync, last sync time update).
        """
        account_name = account.get("friendly_name")
        sync_info = self.storage_manager.get_last_sync_info(account_name)
        is_offline = local_only
        sync_error = None
        
        if not local_only:
            try:
                mail = self._connect_imap(account, auth_password)
            
                res, data = mail.select("INBOX")
                if res != "OK":
                    raise Exception(f"Failed to select INBOX: {str(data)}")
                
                # 1. Construct Search Query
                search_query_args = []
                if search_criteria:
                    if search_criteria.get("keyword"):
                        search_query_args.extend(["OR", "SUBJECT", search_criteria["keyword"], "BODY", search_criteria["keyword"]])
                    if search_criteria.get("from"):
                        search_query_args.extend(["FROM", search_criteria["from"]])
                    if search_criteria.get("since"):
                        try:
                            since_val = search_criteria["since"]
                            if re.match(r'\d{1,2}-[A-Za-z]{3}-\d{4}', since_val):
                                since_date = since_val
                            else:
                                since_date = datetime.strptime(since_val, "%Y-%m-%d").strftime("%d-%b-%Y")
                            search_query_args.extend(["SINCE", since_date])
                        except: pass
                    if search_criteria.get("before"):
                        try:
                            before_val = search_criteria["before"]
                            if re.match(r'\d{1,2}-[A-Za-z]{3}-\d{4}', before_val):
                                before_date = before_val
                            else:
                                before_date = datetime.strptime(before_val, "%Y-%m-%d").strftime("%d-%b-%Y")
                            search_query_args.extend(["BEFORE", before_date])
                        except: pass
                
                if not search_query_args:
                    search_query_args.append("ALL")

                # Helper to encode non-ASCII tokens to bytes (imaplib will send as literals)
                # but keep ASCII as strings (imaplib will send as quoted strings or atoms)
                def process_token(t):
                    if not isinstance(t, str): return t
                    try:
                        t.encode('ascii')
                        return t
                    except UnicodeEncodeError:
                        return t.encode('utf-8')

                # Strategy: Try ASCII first, if fails or contains non-ASCII, try UTF-8
                # If UTF-8 fails (BAD command), fallback to local and warn user
                try:
                    # 1. Try standard search (no charset specified, assumes ASCII)
                    # This is most compatible with older servers
                    res, data = mail.uid('search', None, *search_query_args)
                except (imaplib.IMAP4.error, UnicodeEncodeError, TypeError):
                    # If standard search fails due to non-ASCII or server error, try UTF-8
                    try:
                        final_args = [process_token(arg) for arg in search_query_args]
                        res, data = mail.uid('search', "UTF-8", *final_args)
                    except (imaplib.IMAP4.error, TypeError) as e:
                        # Server doesn't support UTF-8 search or command is BAD
                        is_offline = True
                        sync_error = f"IMAP search failed (UTF-8 not supported?): {str(e)}"
                        # We return results from cache if is_offline is True
                        res = "FAILED"
                        
                if res == "OK":
                    uids_raw = data[0].split()
                    
                    # We only need the top 'limit' results (newest first)
                    view_uids = uids_raw[-limit:] if limit > 0 and len(uids_raw) > limit else uids_raw
                    view_uids = list(reversed(view_uids)) # Newest first
                    
                    results = []
                    # Fetch metadata for each UID to be more robust against buggy IMAP servers
                    for uid_bin in view_uids:
                        uid_str = uid_bin.decode()
                        res_m, msg_data = mail.uid('fetch', uid_bin, '(FLAGS BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])')
                        
                        if res_m == "OK" and msg_data:
                            for item in msg_data:
                                if isinstance(item, tuple):
                                    resp_text = item[0].decode()
                                    header_bytes = item[1]
                                    
                                    msg = email.message_from_bytes(header_bytes)
                                    
                                    # Parse basic metadata
                                    try:
                                        subject_header = msg.get("Subject")
                                        subject = str(make_header(decode_header(subject_header))) if subject_header else "No Subject"
                                    except: subject = "No Subject"
                                    
                                    try:
                                        from_header = str(make_header(decode_header(msg.get("From", "Unknown"))))
                                    except: from_header = "Unknown"
                                    
                                    name, email_addr = parseaddr(from_header)
                                    sender_name = name or (from_header.split("<")[0].strip() if "<" in from_header else from_header)
                                    
                                    results.append({
                                        "id": uid_str,
                                        "from": sender_name,
                                        "from_email": email_addr,
                                        "subject": subject,
                                        "date": msg.get("Date"),
                                        "seen": '\\Seen' in resp_text
                                    })
                                    break # Only one tuple per fetch
                        
                    mail.close()
                    mail.logout()
                    return results, {"last_sync": sync_info.get("time"), "is_offline": False}
                
                # If we reach here, search failed but wasn't caught by socket.timeout
                # Close connection if still open
                try:
                    mail.logout()
                except: pass
                
            except socket.timeout as e:
                is_offline = True
                sync_error = f"Connection timeout: {str(e)}"
            except Exception as e:
                # SSL, Protocol errors, or other bugs: re-raise directly, don't fallback to cache
                raise e
            
        # Offline (timeout) or local_only: return from cache
        cached_emails = self.storage_manager.get_emails_from_cache(account_name, limit, search_criteria, auth_password)
        return cached_emails, {"last_sync": sync_info.get("time"), "is_offline": is_offline, "error": sync_error if is_offline else None}

    def _parse_email(self, uid_str, msg, status_data):
        """Helper to parse email message object into dict."""
        try:
            subject_header = msg.get("Subject")
            subject = str(make_header(decode_header(subject_header))) if subject_header else "No Subject"
        except: subject = "No Subject"
        
        try:
            from_header = str(make_header(decode_header(msg.get("From", "Unknown"))))
        except: from_header = "Unknown"
        
        name, email_addr = parseaddr(from_header)
        sender_name = name or (from_header.split("<")[0].strip() if "<" in from_header else from_header)
        sender_name = sender_name.replace('"', '').replace("'", "").strip()
        if not sender_name or sender_name == email_addr:
            sender_name = email_addr or from_header

        content = ""
        html_content = ""
        if msg.is_multipart():
            for part in msg.walk():
                c_type = part.get_content_type()
                if c_type == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    try: content = part.get_payload(decode=True).decode(charset, errors="replace")
                    except: content = part.get_payload(decode=True).decode("utf-8", errors="replace")
                elif c_type == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    try: html_content = part.get_payload(decode=True).decode(charset, errors="replace")
                    except: html_content = part.get_payload(decode=True).decode("utf-8", errors="replace")
        else:
            c_type = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            if c_type == "text/plain":
                try: content = msg.get_payload(decode=True).decode(charset, errors="replace")
                except: content = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            elif c_type == "text/html":
                try: html_content = msg.get_payload(decode=True).decode(charset, errors="replace")
                except: html_content = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        
        return {
            "id": uid_str,
            "from": sender_name,
            "from_email": email_addr,
            "subject": subject,
            "date": msg.get("Date"),
            "seen": '\\Seen' in str(status_data),
            "content": content or html_content,
            "content_type": "text/plain" if content else "html_only"
        }

    def read_email(self, account, auth_password, email_id):
        """
        Read email content. Priority: Local Cache > Remote Server.
        """
        account_name = account.get("friendly_name")
        
        # 1. Priority: Local Cache
        content_type, content = self.storage_manager.get_email_content(account_name, email_id, auth_password)
        if content:
            # Mark as seen locally
            self.storage_manager.update_email_seen_status(account_name, email_id, True)
            
            # Optional: Try to mark as seen on server (best effort, don't block/fail if offline)
            try:
                mail = self._connect_imap(account, auth_password)
                mail.select("INBOX")
                mail.uid('store', email_id, '+FLAGS', '\\Seen')
                mail.logout()
            except:
                # If offline, we could record a pending 'mark as seen' action here if we had one
                pass
                
            if content_type == "html_only":
                return {"type": "html_only", "html": content}
            return content

        # 2. Fallback: Remote Server
        try:
            mail = self._connect_imap(account, auth_password)
            mail.select("INBOX")
            # Mark as seen on server
            mail.uid('store', email_id, '+FLAGS', '\\Seen')
            # Fetch content
            res, msg_data = mail.uid('fetch', email_id, "(RFC822)")
            
            final_content = ""
            final_type = "text/plain"
            if res == "OK":
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        # We just marked it as seen on server, so we should save it as seen in cache too
                        status_data = f"{part[0].decode()} (FLAGS (\\Seen))"
                        parsed = self._parse_email(email_id, msg, status_data)
                        
                        final_content = parsed["content"]
                        final_type = parsed["content_type"]
                        
                        # Save to cache including metadata and full content
                        self.storage_manager.save_emails_to_cache(account_name, [parsed], auth_password)
            
            mail.close()
            mail.logout()
            
            if final_type == "html_only":
                return {"type": "html_only", "html": final_content}
            return final_content

        except Exception as e:
            return f"Error fetching from server: {e}"

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
        account_name = account.get("friendly_name") or account.get("name")
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
