import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formatdate
from pathlib import Path
from typing import Any, Callable
from .connector import MailConnector

class MailSender:
    def __init__(self, connector: MailConnector, config_obj: dict[str, Any], save_config_callback: Callable[[], None]):
        self.connector = connector
        self.config = config_obj
        self.save_config_callback = save_config_callback

    def send_email(self, account: dict[str, Any], password: str, to: str, subject: str, body: str, attachments: list[str] | None = None) -> None:
        """Sends an email using SMTP with either password or OAuth2 authentication."""
        # Decrypt auth only for getting the username
        auth = self.connector.auth_manager.decrypt_account_auth(account, password)
        sender_email = auth.get("username")
        friendly_name = account.get("friendly_name") or ""
        
        msg = MIMEMultipart()
        msg['From'] = f"{friendly_name} <{sender_email}>" if friendly_name else sender_email
        msg['To'] = to
        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)
        msg.attach(MIMEText(body, 'plain'))

        if attachments:
            for file_path in attachments:
                path = Path(file_path)
                if path.exists():
                    with path.open("rb") as f:
                        part = MIMEApplication(f.read(), Name=path.name)
                    part['Content-Disposition'] = f'attachment; filename="{path.name}"'
                    msg.attach(part)

        try:
            server = self.connector.get_smtp_connection(account, password)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            raise e
