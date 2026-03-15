import imaplib
import re
from typing import Any, List
from logger import setup_logger

logger = setup_logger("folder_manager")

class MailFolderManager:
    def __init__(self, connector: Any) -> None:
        self.connector = connector

    def list_folders(self, mail: imaplib.IMAP4) -> List[str]:
        """List all available folders/mailboxes."""
        res, data = mail.list()
        folders = []
        if res == "OK":
            for item in data:
                if isinstance(item, bytes):
                    decoded = item.decode()
                    # Try to match the quoted name at the end
                    match = re.search(r'"([^"]+)"$', decoded)
                    if match:
                        folders.append(match.group(1))
                    else:
                        # If not quoted, take the last part
                        parts = decoded.split()
                        if parts:
                            folders.append(parts[-1])
        return folders

    def get_folder_status(self, mail: imaplib.IMAP4, folder_name: str) -> dict[str, int]:
        """Get status of a specific folder (messages, unseen)."""
        # Ensure folder name is quoted if it contains spaces
        quoted_folder = f'"{folder_name}"' if " " in folder_name else folder_name
        res, data = mail.status(quoted_folder, "(MESSAGES UNSEEN)")
        status = {"messages": 0, "unseen": 0}
        if res == "OK" and data:
            # Format: * STATUS "INBOX" (MESSAGES 10 UNSEEN 2)
            content = data[0].decode()
            msg_match = re.search(r"MESSAGES\s+(\d+)", content)
            unseen_match = re.search(r"UNSEEN\s+(\d+)", content)
            if msg_match:
                status["messages"] = int(msg_match.group(1))
            if unseen_match:
                status["unseen"] = int(unseen_match.group(1))
        return status

    def create_folder(self, mail: imaplib.IMAP4, folder_name: str) -> bool:
        """Create a new folder."""
        res, data = mail.create(folder_name)
        if res != "OK":
            logger.error(f"Failed to create folder {folder_name}: {res} {data}")
        return res == "OK"

    def delete_folder(self, mail: imaplib.IMAP4, folder_name: str) -> bool:
        """Delete an existing folder."""
        res, data = mail.delete(folder_name)
        if res != "OK":
            logger.error(f"Failed to delete folder {folder_name}: {res} {data}")
        return res == "OK"

    def move_emails(self, mail: imaplib.IMAP4, uids: List[str], source_folder: str, dest_folder: str) -> bool:
        """Move emails from one folder to another."""
        # Ensure source folder is selected
        mail.select(source_folder)
        uids_str = ",".join(uids)
        
        # Check for MOVE capability (RFC 6851)
        res, capabilities = mail.capability()
        has_move = False
        if res == "OK":
            for cap in capabilities:
                if isinstance(cap, bytes) and "MOVE" in cap.decode():
                    has_move = True
                    break
        
        if has_move:
            res, data = mail.uid("MOVE", uids_str, dest_folder)
            if res == "OK":
                return True
            logger.warning(f"MOVE failed even with capability: {res} {data}, falling back to COPY/DELETE")

        # Fallback: Copy to destination
        res, data = mail.uid("COPY", uids_str, dest_folder)
        if res == "OK":
            # Mark as deleted in source
            mail.uid("STORE", uids_str, "+FLAGS", "(\\Deleted)")
            mail.expunge()
            return True
            
        logger.error(f"Failed to move emails (COPY failed): {res} {data}")
        return False
