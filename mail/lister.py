import imaplib
import email
from typing import Any, Dict, List, Optional, Tuple
from .storage_manager import Email, MailStorageManager
from .connector import MailConnector
from .parser import MailParser
from logger import setup_logger

logger = setup_logger("lister")

class MailLister:
    """Handles querying and listing emails from local cache or remote server."""
    
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

    def query_emails(
        self, 
        account: dict[str, Any], 
        auth_password: str, 
        limit: int = 20, 
        search_criteria: dict[str, Any] | None = None, 
        local_only: bool = False,
        sort_by: str = "date",
        order: str = "desc"
    ) -> tuple[list[Email | dict[str, Any]], dict[str, Any]]:
        """Query emails from cache or server."""
        account_name = account.get("friendly_name", "Unknown")
        folder = search_criteria.get("folder") if search_criteria else None
        is_offline = local_only
        sync_error: str | None = None
        
        # If folder is specified and not local_only, try remote query
        if not local_only and folder:
            try:
                mail = self.connector.get_imap_connection(account, auth_password)
                res, data = mail.select(folder)
                if res == "OK":
                    # Simple remote query - doesn't use all search_criteria for now
                    # but could be extended to use IMAP search
                    res_s, data_s = mail.uid('search', None, "ALL")
                    if res_s == "OK":
                        uids_raw = data_s[0].split()
                        view_uids = uids_raw[-limit:] if limit > 0 and len(uids_raw) > limit else uids_raw
                        view_uids = list(reversed(view_uids))
                        
                        results: list[dict[str, Any]] = []
                        for uid_bin in view_uids:
                            uid_str = uid_bin.decode()
                            res_m, msg_data = mail.uid('fetch', uid_bin, '(FLAGS BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])')
                            if res_m == "OK" and msg_data:
                                for item in msg_data:
                                    if isinstance(item, tuple):
                                        msg = email.message_from_bytes(item[1])
                                        results.append(MailParser.parse_basic_metadata(uid_str, msg, item[0].decode(), folder))
                                        break
                        mail.close()
                        mail.logout()
                        return results, {"last_sync": "Online", "is_offline": False}
                mail.logout()
            except Exception as e:
                logger.error(f"Remote query failed for {account_name} [{folder}]: {e}")
                is_offline = True
                sync_error = str(e)
            
        # Fallback to local cache
        cached_emails = self.storage_manager.get_emails_from_cache(
            account_name, limit, search_criteria, auth_password, 
            folder=folder, sort_by=sort_by, sort_order=order
        )
        return cached_emails, {
            "last_sync": "Local", 
            "is_offline": is_offline, 
            "is_fallback": is_offline and not local_only,
            "error": sync_error
        }
