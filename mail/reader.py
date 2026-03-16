import imaplib
import email
from typing import Any, Dict, List, Optional, Tuple
from .storage_manager import Email, MailStorageManager
from .connector import MailConnector
from .parser import MailParser
from logger import setup_logger

logger = setup_logger("reader")

class MailReader:
    """Handles reading full emails from local cache or remote server."""
    
    def __init__(
        self, 
        connector: MailConnector,
        storage_manager: MailStorageManager, 
        config: dict[str, Any], 
        save_config_callback: Any
    ) -> None:
        self.connector = connector
        self.storage_manager = storage_manager
        self.config = config
        self.save_config_callback = save_config_callback

    def read_email(self, account: dict[str, Any], auth_password: str, email_id: str, folder: str = "INBOX") -> Email | str:
        """Read full email content. Priority: Local Cache > Remote Server."""
        account_name = account.get("friendly_name", "Unknown")
        
        # 1. Priority: Local Cache
        if (details := self.storage_manager.get_email_full_details(account_name, email_id, auth_password, folder)) and details.get("content"):
            self.storage_manager.update_seen_status(account_name, email_id, True, folder)
            
            # Async best-effort mark as seen on server
            try:
                mail = self.connector.get_imap_connection(account, auth_password)
                mail.select(folder)
                mail.uid('STORE', email_id, '+FLAGS', '(\\Seen)')
                mail.logout()
            except Exception as e:
                logger.debug(f"Failed to mark as seen on server for {email_id}: {e}")
            
            return Email(
                account_name=account_name,
                folder=folder,
                uid=email_id,
                sender=details.get("from", ""),
                sender_email=details.get("from_email", ""),
                subject=details.get("subject", ""),
                date=details.get("date", ""),
                seen=True,
                content_type=details.get("content_type", "text/plain"),
                content=details.get("content", ""),
                attachments=details.get("attachments", [])
            )

        # 2. Fallback: Remote Server
        try:
            mail = self.connector.get_imap_connection(account, auth_password)
            mail.select(folder)
            mail.uid('STORE', email_id, '+FLAGS', '(\\Seen)')
            res, msg_data = mail.uid('fetch', email_id, "(RFC822)")
            
            parsed: Email | None = None
            if res == "OK" and msg_data:
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        status_data = f"{part[0].decode()} (FLAGS (\\Seen))"
                        parsed = MailParser.parse_full_email(account_name, email_id, msg, status_data, folder)
                        self.storage_manager.save_emails_to_cache(account_name, folder, [parsed.to_dict()], auth_password)
                        break
            
            mail.close()
            mail.logout()
            return parsed if parsed else "Failed to fetch email content."

        except Exception as e:
            logger.error(f"Error reading email {email_id} on {account_name} [{folder}]: {e}")
            return f"Error: {e}"
