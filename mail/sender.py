import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

class MailSender:
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager

    def send_email(self, account, password, to, subject, body, attachments=None):
        auth = self.auth_manager.decrypt_account_auth(account, password)
        
        msg = MIMEMultipart()
        msg['From'] = account['friendly_name']
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                    msg.attach(part)

        # Connect to SMTP
        server = smtplib.SMTP_SSL(account['smtp_server'], account['smtp_port'])
        
        if account['login_method'] == "Account/Password":
            server.login(auth['username'], auth['password'])
        else:
            # OAuth2 authentication (XOAUTH2) for SMTP
            user = auth.get("username")
            token = auth.get("access_token")
            auth_string = f"user={user}\x01auth=Bearer {token}\x01\x01"
            try:
                server.authenticate('XOAUTH2', lambda x: auth_string)
            except smtplib.SMTPAuthenticationError:
                # Try refresh
                new_token = self.auth_manager.refresh_oauth2_token(account, auth, password, {}) # Note: we'd need config here or handle it in manager
                if new_token:
                    auth_string = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                    server.authenticate('XOAUTH2', lambda x: auth_string)
                else:
                    raise

        server.send_message(msg)
        server.quit()
