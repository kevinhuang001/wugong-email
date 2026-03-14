import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

class MailSender:
    def __init__(self, auth_manager, config, save_config_callback):
        self.auth_manager = auth_manager
        self.config = config
        self.save_config_callback = save_config_callback

    def send_email(self, account, password, to, subject, body, attachments=None):
        auth = self.auth_manager.decrypt_account_auth(account, password)
        sender_email = auth.get("username")
        friendly_name = account.get("friendly_name") or ""
        
        msg = MIMEMultipart()
        if friendly_name:
            msg['From'] = f"{friendly_name} <{sender_email}>"
        else:
            msg['From'] = sender_email
            
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
        smtp_server = account['smtp_server']
        smtp_port = int(account['smtp_port'])
        tls_method = account.get('smtp_tls_method', 'SSL/TLS' if smtp_port == 465 else ('STARTTLS' if smtp_port == 587 else 'Plain'))
        
        try:
            if tls_method == "SSL/TLS":
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.ehlo()
                if tls_method == "STARTTLS" and server.has_extn('STARTTLS'):
                    server.starttls()
                    server.ehlo()
            
            if account['login_method'] == "Account/Password":
                server.login(auth['username'], auth['password'])
            else:
                # OAuth2 authentication (XOAUTH2) for SMTP
                user = auth.get("username")
                token = auth.get("access_token")
                
                def do_auth(t):
                    auth_str = f"user={user}\x01auth=Bearer {t}\x01\x01"
                    # Use docmd for XOAUTH2 as some smtplib versions don't have authenticate()
                    # or it doesn't support XOAUTH2 well
                    import base64
                    encoded_auth = base64.b64encode(auth_str.encode()).decode()
                    status, resp = server.docmd("AUTH", f"XOAUTH2 {encoded_auth}")
                    if status != 235:
                        raise smtplib.SMTPAuthenticationError(status, resp)

                try:
                    do_auth(token)
                except smtplib.SMTPAuthenticationError:
                    # Try refresh
                    new_token = self.auth_manager.refresh_oauth2_token(account, auth, password, self.config)
                    if new_token:
                        self.save_config_callback()
                        do_auth(new_token)
                    else:
                        raise

            # Log details for debugging
            # print(f"DEBUG: Sending from {msg['From']} to {msg['To']} via {smtp_server}:{smtp_port}")
            server.send_message(msg)
            server.quit()
        except Exception as e:
            # print(f"DEBUG: SMTP Error: {e}")
            raise e
