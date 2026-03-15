import imaplib
import logging
from typing import Any, Tuple, Optional
from .storage_manager import MailStorageManager
from .connector import MailConnector

logger = logging.getLogger("deleter")

class MailDeleter:
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

    def delete_email(self, account: dict[str, Any], auth_password: str, email_id: str, folder: str = "INBOX") -> Tuple[bool, str]:
        """Delete an email from server and cache."""
        account_name = account.get("friendly_name") or "Unknown"
        mail: imaplib.IMAP4 | None = None
        try:
            mail = self.connector.get_imap_connection(account, auth_password)
            res, _ = mail.select(folder)
            if res != "OK":
                raise Exception(f"Failed to select folder {folder}")
            
            mail.uid('STORE', email_id, '+FLAGS', '(\\Deleted)')
            mail.expunge()
            
            self.storage_manager.delete_email_from_cache(account_name, email_id, folder)
            mail.close()
            mail.logout()
            logger.info(f"Deleted email {email_id} from {account_name} [{folder}]")
            return True, "Email deleted successfully."
            
        except Exception as e:
            logger.warning(f"Deletion failed for {email_id} on {account_name} [{folder}]: {e}")
            self.storage_manager.add_pending_action(account_name, 'delete', email_id, folder)
            self.storage_manager.delete_email_from_cache(account_name, email_id, folder)
            if mail:
                try: mail.logout()
                except: pass
            return False, f"Network issue: Deletion scheduled. Local cache updated."

    def sync_pending_actions(self, account: dict[str, Any], auth_password: str) -> None:
        """Process pending deletions."""
        account_name = account.get("friendly_name") or "Unknown"
        if not (pending_actions := self.storage_manager.get_pending_actions(account_name)):
            return
            
        mail: imaplib.IMAP4 | None = None
        processed_ids: list[int] = []
        try:
            mail = self.connector.get_imap_connection(account, auth_password)
            
            # Group actions by folder
            folder_actions = {}
            for action_id, action_type, uid, folder in pending_actions:
                if action_type == 'delete':
                    if folder not in folder_actions:
                        folder_actions[folder] = []
                    folder_actions[folder].append((action_id, uid))
            
            for folder, actions in folder_actions.items():
                res, _ = mail.select(folder)
                if res == "OK":
                    for action_id, uid in actions:
                        try:
                            mail.uid('STORE', uid, '+FLAGS', '(\\Deleted)')
                            processed_ids.append(action_id)
                        except Exception as e:
                            logger.error(f"Failed to process pending deletion for UID {uid} in {folder}: {e}")
                    mail.expunge()
                    mail.close()
            
            if processed_ids:
                for action_id in processed_ids:
                    self.storage_manager.remove_pending_action(action_id)
                logger.info(f"Processed {len(processed_ids)} pending deletions for {account_name}")
            
            mail.logout()
        except Exception as e:
            logger.warning(f"Failed to sync pending actions for {account_name}: {e}")
            if mail:
                try: mail.logout()
                except: pass
