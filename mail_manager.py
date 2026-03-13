import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import toml
import base64
import requests
import os
from crypto_utils import decrypt_data, encrypt_data

class MailManager:
    def __init__(self, config_path=None):
        if config_path is None:
            # Check environment variable, then default user config path, then local
            env_path = os.environ.get("WUGONG_CONFIG")
            user_path = os.path.expanduser("~/.config/wugong/config.toml")
            if env_path and os.path.exists(env_path):
                self.config_path = env_path
            elif os.path.exists(user_path):
                self.config_path = user_path
            else:
                self.config_path = "config.toml"
        else:
            self.config_path = config_path
            
        self.config = self._load_config()
        self.accounts = self.config.get("accounts", [])
        self.encryption_enabled = self.config.get("general", {}).get("encryption_enabled", False)
        self.salt = base64.b64decode(self.config.get("general", {}).get("salt", "")) if self.encryption_enabled else None

    def _load_config(self):
        try:
            return toml.load(self.config_path)
        except:
            return {}

    def get_account_by_name(self, friendly_name):
        for acc in self.accounts:
            if acc.get("friendly_name") == friendly_name:
                return acc
        return None

    def decrypt_account_auth(self, account, password):
        auth = account.get("auth", {})
        decrypted_auth = {}
        sensitive_keys = ["password", "client_id", "client_secret", "refresh_token", "access_token"]
        
        for k, v in auth.items():
            # Check if this is an encrypted string (should be a base64 string if encrypted)
            # and if encryption is enabled for this account's fields
            if self.encryption_enabled and k in sensitive_keys and isinstance(v, str) and v:
                try:
                    decrypted_auth[k] = decrypt_data(v, password, self.salt)
                except Exception as e:
                    # If decryption fails, it might be because it's not actually encrypted or wrong password
                    # For now we raise to inform the user
                    raise Exception(f"Decryption failed for {k}: {e}")
            else:
                decrypted_auth[k] = v
        return decrypted_auth

    def _save_config(self):
        with open(self.config_path, "w") as f:
            toml.dump(self.config, f)

    def _refresh_oauth2_token(self, account, auth, password):
        """Refreshes the OAuth2 access token and saves it back to config.toml"""
        refresh_token = auth.get("refresh_token")
        if not refresh_token:
            return False

        print(f"🔄 Refreshing OAuth2 token for '{account.get('friendly_name')}'...")
        
        payload = {
            'client_id': auth.get('client_id'),
            'client_secret': auth.get('client_secret'),
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': " ".join(auth.get('scopes', []))
        }
        
        try:
            response = requests.post(auth.get('token_url'), data=payload)
            response.raise_for_status()
            token_data = response.json()
            
            new_access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token', refresh_token) # Some providers don't return a new refresh token
            
            # Update local config structure
            for acc in self.config.get("accounts", []):
                if acc.get("friendly_name") == account.get("friendly_name"):
                    if self.encryption_enabled:
                        acc["auth"]["access_token"] = encrypt_data(new_access_token, password, self.salt)
                        acc["auth"]["refresh_token"] = encrypt_data(new_refresh_token, password, self.salt)
                    else:
                        acc["auth"]["access_token"] = new_access_token
                        acc["auth"]["refresh_token"] = new_refresh_token
                    break
            
            # Persist to file
            self._save_config()
            return new_access_token
        except Exception as e:
            print(f"❌ Failed to refresh token: {e}")
            return None

    def get_email_content(self, account, auth_password, email_id):
        auth = self.decrypt_account_auth(account, auth_password)
        
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
                new_token = self._refresh_oauth2_token(account, auth, auth_password)
                if new_token:
                    mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
                    auth_string = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                    mail.authenticate('XOAUTH2', lambda x: auth_string)
                else:
                    raise Exception("Authentication failed.")

        mail.select("INBOX")
        res, msg_data = mail.fetch(email_id, "(RFC822)")
        
        content = ""
        if res == "OK":
            for part in msg_data:
                if isinstance(part, tuple):
                    msg = email.message_from_bytes(part[1])
                    
                    # Get body
                    if msg.is_multipart():
                        for subpart in msg.walk():
                            content_type = subpart.get_content_type()
                            content_disposition = str(subpart.get("Content-Disposition"))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                charset = subpart.get_content_charset() or "utf-8"
                                content = subpart.get_payload(decode=True).decode(charset, errors="replace")
                                break
                    else:
                        charset = msg.get_content_charset() or "utf-8"
                        content = msg.get_payload(decode=True).decode(charset, errors="replace")
        
        mail.close()
        mail.logout()
        return content

    def fetch_emails(self, account, auth_password, limit=10, search_criteria=None):
        auth = self.decrypt_account_auth(account, auth_password)
        
        # Connect to IMAP
        mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
        
        if account['login_method'] == "Account/Password":
            mail.login(auth['username'], auth['password'])
        else:
            # OAuth2 authentication (XOAUTH2)
            user = auth.get("username")
            token = auth.get("access_token")
            if not user or not token:
                raise Exception(f"OAuth2 config for '{account.get('friendly_name')}' is incomplete. Please re-run 'python wizard.py' to add the required Email Account (username).")
            
            try:
                auth_string = f"user={user}\x01auth=Bearer {token}\x01\x01"
                mail.authenticate('XOAUTH2', lambda x: auth_string)
            except imaplib.IMAP4.error as e:
                # If authentication failed, try refreshing the token
                new_token = self._refresh_oauth2_token(account, auth, auth_password)
                if new_token:
                    # Reconnect and try again with new token
                    mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
                    auth_string = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                    mail.authenticate('XOAUTH2', lambda x: auth_string)
                else:
                    raise Exception(f"Authentication failed and token refresh failed: {e}")

        mail.select("INBOX")
        
        # Build IMAP search query
        query = "ALL"
        if search_criteria:
            query_parts = []
            if search_criteria.get("keyword"):
                query_parts.append(f'TEXT "{search_criteria["keyword"]}"')
            if search_criteria.get("from"):
                query_parts.append(f'FROM "{search_criteria["from"]}"')
            if search_criteria.get("since"):
                # Date format: 01-Jan-2023
                query_parts.append(f'SINCE {search_criteria["since"]}')
            if search_criteria.get("before"):
                query_parts.append(f'BEFORE {search_criteria["before"]}')
            
            if query_parts:
                query = " ".join(query_parts)

        status, messages = mail.search(None, query)
        
        email_list = []
        if status == "OK":
            # Get latest emails
            msg_ids = messages[0].split()
            # If search returned many results, we still respect the limit from the end (latest)
            count = 0
            for i in range(len(msg_ids) - 1, -1, -1):
                if count >= limit:
                    break
                    
                res, msg_data = mail.fetch(msg_ids[i], "(RFC822 FLAGS)")
                if res == "OK":
                    raw_email = None
                    flags = []
                    for part in msg_data:
                        if isinstance(part, tuple):
                            raw_email = part[1]
                            # Extract flags from the response
                            # The response looks like: b'1 (RFC822 {1234} FLAGS (\\Seen \\Recent) ...)'
                            resp_str = part[0].decode('utf-8', errors='ignore')
                            if 'FLAGS' in resp_str:
                                import re
                                flags_match = re.search(r'FLAGS \((.*?)\)', resp_str)
                                if flags_match:
                                    flags = flags_match.group(1).split()
                    
                    if raw_email:
                        msg = email.message_from_bytes(raw_email)
                        subject, encoding = decode_header(msg.get("Subject", "No Subject"))[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8", errors="replace")
                        
                        from_, encoding = decode_header(msg.get("From", "Unknown"))[0]
                        if isinstance(from_, bytes):
                            from_ = from_.decode(encoding if encoding else "utf-8", errors="replace")
                        
                        is_seen = "\\Seen" in flags
                        
                        email_list.append({
                            "id": msg_ids[i].decode(),
                            "from": from_,
                            "subject": subject,
                            "date": msg.get("Date", "N/A"),
                            "seen": is_seen
                        })
                        count += 1
        
        mail.close()
        mail.logout()
        return email_list

    def send_email(self, account, auth_password, to, subject, body, attachments=None):
        auth = self.decrypt_account_auth(account, auth_password)
        
        # Create message
        if attachments:
            msg = MIMEMultipart()
            msg.attach(MIMEText(body))
        else:
            msg = MIMEText(body)
            
        msg['Subject'] = subject
        msg['From'] = auth['username']
        msg['To'] = to
        
        if attachments:
            for file_path in attachments:
                if not os.path.exists(file_path):
                    continue
                with open(file_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                    msg.attach(part)
        
        # Connect to SMTP
        # Gmail/Outlook usually use TLS on 587 or SSL on 465
        if account['smtp_port'] == 465:
            server = smtplib.SMTP_SSL(account['smtp_server'], account['smtp_port'])
        else:
            server = smtplib.SMTP(account['smtp_server'], account['smtp_port'])
            server.starttls()
            
        if account['login_method'] == "Account/Password":
            server.login(auth['username'], auth['password'])
        else:
            # OAuth2 authentication (XOAUTH2)
            user = auth.get("username")
            token = auth.get("access_token")
            
            try:
                auth_string = f"user={user}\x01auth=Bearer {token}\x01\x01"
                server.docmd("AUTH", "XOAUTH2 " + base64.b64encode(auth_string.encode()).decode())
            except smtplib.SMTPException:
                # Try refreshing token
                new_token = self._refresh_oauth2_token(account, auth, auth_password)
                if new_token:
                    auth_string = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                    server.docmd("AUTH", "XOAUTH2 " + base64.b64encode(auth_string.encode()).decode())
                else:
                    raise Exception("SMTP Authentication failed and token refresh failed.")
        
        server.send_message(msg)
        server.quit()
        return True
