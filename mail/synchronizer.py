import imaplib
import email
from email.utils import parseaddr
from datetime import datetime
import re
import socket
from typing import Any, Callable, cast, Dict, List, Optional, Tuple

from .storage_manager import Email, MailStorageManager
from .connector import MailConnector
from .parser import MailParser
from logger import setup_logger

logger = setup_logger("syncer")

class MailSynchronizer:
    def __init__(
        self, 
        connector: MailConnector,
        storage_manager: MailStorageManager, 
        config: dict[str, Any], 
        save_config_callback: Callable[[], None]
    ) -> None:
        self.connector = connector
        self.storage_manager = storage_manager
        self.config = config
        self.save_config_callback = save_config_callback

    def _imap_search(self, mail: imaplib.IMAP4, search_query_args: list[str | bytes]) -> tuple[str, list[bytes]]:
        """Robust IMAP search with 3 fallback methods."""
        has_non_ascii = False
        keyword: str | None = None
        for i, arg in enumerate(search_query_args):
            if arg == "TEXT" and i + 1 < len(search_query_args):
                keyword = cast(str, search_query_args[i+1])
            
            try:
                if isinstance(arg, bytes):
                    arg.decode('ascii')
                else:
                    arg.encode('ascii')
            except (UnicodeEncodeError, UnicodeDecodeError):
                has_non_ascii = True
        
        if not has_non_ascii:
            try:
                res = mail.uid('search', None, *search_query_args)
                return res
            except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
                logger.debug(f"ASCII search failed, falling back: {e}")
                has_non_ascii = True
            except socket.timeout:
                raise
            except Exception as e:
                logger.debug(f"Unexpected search error, falling back: {e}")
                has_non_ascii = True

        if getattr(mail, '_utf8_enabled', False):
            try:
                res, data = mail.uid("SEARCH", None, "TEXT", f'"{keyword}"') if keyword else mail.uid("SEARCH", None, *search_query_args)
                if res == "OK": return res, data
            except Exception as e:
                logger.debug(f"UTF8 search failed: {e}")

        try:
            if keyword:
                keyword_bytes = keyword.encode("utf-8") if isinstance(keyword, str) else keyword
                res, data = mail.uid('SEARCH', 'CHARSET', 'UTF-8', 'TEXT', keyword_bytes)
            else:
                final_args = [a.encode("utf-8") if isinstance(a, str) else a for a in search_query_args]
                res, data = mail.uid('SEARCH', 'CHARSET', 'UTF-8', *final_args)
            if res == "OK": return res, data
        except Exception as e:
            logger.debug(f"UTF-8 search failed: {e}")

        res = mail.uid('search', None, *search_query_args)
        return res

    def sync_emails(
        self, 
        account: dict[str, Any], 
        auth_password: str, 
        limit: int = 20, 
        search_criteria: dict[str, Any] | None = None, 
        progress_callback: Callable[[int, int, str], None] | None = None, 
        is_initial_sync: bool = False,
        folder: str = "INBOX"
    ) -> tuple[list[Email], dict[str, Any]]:
        """Sync emails between server and local cache."""
        account_name = account.get("friendly_name", "Unknown")
        sync_info = self.storage_manager.get_last_sync_info(account_name, folder)
        is_offline = False
        newly_fetched_emails: list[Email] = []
        sync_error: str | None = None
        
        try:
            mail = self.connector.get_imap_connection(account, auth_password)
            res, data = mail.select(folder)
            if res != "OK":
                raise Exception(f"Failed to select folder {folder}: {data}")
            
            search_query_args = self._build_search_query(search_criteria, is_initial_sync, limit, sync_info)
            logger.info(f"Syncing {account_name} [{folder}] with query: {search_query_args}")

            try:
                res, data = self._imap_search(mail, search_query_args)
            except Exception as e:
                if "UTF-8 not supported" in str(e):
                    is_offline = True
                    sync_error = str(e)
                    res = "FAILED"
                else:
                    raise e

            if res == "OK":
                uids_raw = data[0].split()
                server_uids = {uid.decode() for uid in uids_raw}
                
                # Identify UIDs to process
                if uids_to_process := self._get_uids_to_process(uids_raw, limit, is_initial_sync, search_criteria):
                    newly_fetched_emails = self._sync_emails_internal(
                        mail, account_name, folder, uids_to_process, auth_password, progress_callback
                    )
                
                # Update sync status
                new_last_uid = uids_raw[-1].decode() if uids_raw else sync_info.get("uid", "0")
                self.storage_manager.update_sync_info(account_name, folder, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), new_last_uid)
                sync_info = self.storage_manager.get_last_sync_info(account_name, folder)

            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"Sync error for {account_name} [{folder}]: {e}")
            is_offline = True
            sync_error = str(e)

        email_list = self.storage_manager.get_emails_from_cache(account_name, limit, search_criteria, auth_password, folder=folder)
        return email_list, {
            "last_sync": sync_info.get("time"), 
            "is_offline": is_offline, 
            "is_fallback": is_offline,
            "new_emails": newly_fetched_emails,
            "error": sync_error
        }

    def _build_search_query(
        self, 
        search_criteria: dict[str, Any] | None, 
        is_initial_sync: bool, 
        limit: int, 
        sync_info: dict[str, Any]
    ) -> list[str | bytes]:
        if is_initial_sync:
            return ["ALL"]

        query: list[str | bytes] = []
        if search_criteria:
            if kw := search_criteria.get("keyword"): query.extend(["TEXT", kw])
            if frm := search_criteria.get("from"): query.extend(["FROM", frm])
            if since := search_criteria.get("since"): query.extend(["SINCE", self._format_date(since)])
            if before := search_criteria.get("before"): query.extend(["BEFORE", self._format_date(before)])
        
        if not query:
            if limit == -1 or limit > 0:
                query.append("ALL")
            elif time := sync_info.get("time"):
                if time != "Never":
                    try:
                        last_date = datetime.strptime(time, "%Y-%m-%d %H:%M:%S").strftime("%d-%b-%Y")
                        query.extend(["SINCE", last_date])
                    except ValueError:
                        query.append("ALL")
                else:
                    query.append("ALL")
        return query

    def _format_date(self, date_str: str) -> str:
        if re.match(r'\d{1,2}-[A-Za-z]{3}-\d{4}', date_str): return date_str
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%b-%Y")
        except ValueError:
            return date_str

    def _get_uids_to_process(self, uids_raw: list[bytes], limit: int, is_initial_sync: bool, search_criteria: dict[str, Any] | None) -> list[bytes]:
        if is_initial_sync:
            return uids_raw if limit == -1 else uids_raw[-limit:]
        if limit > 0 and not search_criteria:
            return uids_raw[-limit:]
        return uids_raw

    def _sync_emails_internal(
        self, 
        mail: imaplib.IMAP4, 
        account_name: str, 
        folder: str,
        uids: list[bytes], 
        auth_password: str,
        progress_callback: Callable[[int, int, str], None] | None
    ) -> list[Email]:
        total = len(uids)
        new_emails: list[Email] = []
        uids_decoded = [u.decode() for u in uids]
        cached_statuses = self.storage_manager.get_cached_statuses(account_name, uids_decoded, folder)
        server_statuses = self._fetch_server_statuses(mail, uids)
        
        for i, uid_bin in enumerate(reversed(uids)):
            uid_str = uid_bin.decode()
            server_seen = server_statuses.get(uid_str, False)
            
            if progress_callback:
                progress_callback(i + 1, total, f"Syncing {i+1}/{total}...")

            if uid_str in cached_statuses:
                if server_seen != cached_statuses[uid_str]:
                    self.storage_manager.update_seen_status(account_name, uid_str, server_seen, folder)
            else:
                res, msg_data = mail.uid('fetch', uid_bin, '(RFC822)')
                if res == "OK" and msg_data[0]:
                    msg = email.message_from_bytes(msg_data[0][1])
                    status_data = f"(FLAGS ({'\\Seen' if server_seen else ''}))"
                    parsed = MailParser.parse_full_email(account_name, uid_str, msg, status_data, folder)
                    new_emails.append(parsed)
        
        if new_emails:
            self.storage_manager.save_emails_to_cache(account_name, folder, [e.to_dict() for e in new_emails], auth_password)
        return new_emails

    def _fetch_server_statuses(self, mail: imaplib.IMAP4, uids: list[bytes]) -> dict[str, bool]:
        statuses: dict[str, bool] = {}
        batch_size = 500
        for i in range(0, len(uids), batch_size):
            batch = uids[i:i + batch_size]
            uids_str = ",".join([u.decode() for u in batch])
            res, data = mail.uid('fetch', uids_str, '(FLAGS)')
            if res == "OK":
                for item in data:
                    if isinstance(item, tuple) and (resp_text := item[0].decode()):
                        if uid_match := re.search(r'UID (\d+)', resp_text):
                            uid = uid_match.group(1)
                            statuses[uid] = '\\Seen' in resp_text
        return statuses
