import imaplib
import email
from email.header import decode_header
from datetime import datetime

class MailReader:
    def __init__(self, auth_manager, storage_manager):
        self.auth_manager = auth_manager
        self.storage_manager = storage_manager

    def fetch_emails(self, account, auth_password, config, save_config_callback, limit=10, search_criteria=None):
        account_name = account.get("friendly_name")
        sync_info = self.storage_manager.get_last_sync_info(account_name)
        is_offline = False
        
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
                    new_token = self.auth_manager.refresh_oauth2_token(account, auth, auth_password, config)
                    if new_token:
                        save_config_callback()
                        mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
                        auth_string = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                        mail.authenticate('XOAUTH2', lambda x: auth_string)
                    else:
                        raise Exception("Authentication failed.")

            mail.select("INBOX")
            
            # Incremental fetch based on UID
            last_uid = sync_info.get("uid", "0")
            search_query = f'UID {int(last_uid)+1}:*' if last_uid != "0" else "ALL"
            res, data = mail.uid('search', None, search_query)
            
            if res == "OK":
                uids = data[0].split()
                # Get the last 'limit' UIDs
                latest_uids = uids[-limit:] if len(uids) > limit else uids
                
                new_emails = []
                for uid in reversed(latest_uids):
                    res, msg_data = mail.uid('fetch', uid, '(RFC822.SIZE BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
                    if res == "OK":
                        raw_msg = msg_data[0][1]
                        msg = email.message_from_bytes(raw_msg)
                        
                        subject, encoding = decode_header(msg.get("Subject", "No Subject"))[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")
                        
                        sender, encoding = decode_header(msg.get("From", "Unknown"))[0]
                        if isinstance(sender, bytes):
                            sender = sender.decode(encoding or "utf-8")
                            
                        new_emails.append({
                            "id": uid.decode(),
                            "from": sender,
                            "subject": subject,
                            "date": msg.get("Date"),
                            "seen": False # New emails are assumed unread for now
                        })
                
                if new_emails:
                    self.storage_manager.save_emails_to_cache(account_name, new_emails, auth_password)
                    # Update sync status
                    new_last_uid = uids[-1].decode() if uids else last_uid
                    self.storage_manager.update_sync_info(account_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), new_last_uid)

            mail.close()
            mail.logout()
            
        except Exception as e:
            is_offline = True

        # Always return from cache (which now includes newly fetched emails)
        email_list = self.storage_manager.get_emails_from_cache(account_name, limit, search_criteria, auth_password)
        return email_list, {"last_sync": sync_info.get("time"), "is_offline": is_offline}

    def read_email(self, account, auth_password, email_id, config, save_config_callback):
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
                    new_token = self.auth_manager.refresh_oauth2_token(account, auth, auth_password, config)
                    if new_token:
                        save_config_callback()
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
