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
                    # Format: (FLAGS) "DELIMITER" "NAME"
                    # Regex explanation:
                    # ^\([^)]*\)\s+   - match flags: (flags) followed by space
                    # "[^"]*"\s+      - match delimiter: "delimiter" followed by space
                    # ("[^"]+"|\S+)   - match folder name: "folder name" or unquoted name
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
