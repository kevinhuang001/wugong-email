from pathlib import Path
from typing import Any
from .authenticator import MailAuthenticator
from .storage_manager import MailStorageManager
from .connector import MailConnector
from .sender import MailSender
from .synchronizer import MailSynchronizer
from .deleter import MailDeleter
from .lister import MailLister
from .reader import MailReader
from .parser import MailParser
from .folder_manager import MailFolderManager
import config

class MailManager:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path or config.get_config_path())
        self.config = config.load_config(str(self.config_path))
        
        general = self.config.get("general", {})
        self.accounts = self.config.get("accounts", [])
        self.encryption_enabled = general.get("encryption_enabled", False)
        self.encrypt_emails = general.get("encrypt_emails", False)
        self.sync_interval = general.get("sync_interval", 10)
        self.salt = config.get_salt(self.config)
        
        # Initialize sub-modules
        self.auth_manager = MailAuthenticator(self.encryption_enabled, self.salt)
        db_path = self.config_path.parent / "cache.db"
        self.storage_manager = MailStorageManager(str(db_path), self.encrypt_emails, self.encryption_enabled, self.salt)
        self.connector = MailConnector(self.auth_manager, self.config, self._save_config)
        
        self.sender = MailSender(self.connector, self.config, self._save_config)
        self.syncer = MailSynchronizer(self.connector, self.storage_manager, self.config, self._save_config)
        self.deleter = MailDeleter(self.connector, self.storage_manager, self.config, self._save_config)
        self.lister = MailLister(self.connector, self.storage_manager, self.config, self._save_config)
        self.reader = MailReader(self.connector, self.storage_manager, self.config, self._save_config)
        self.email_parser = MailParser()
        self.folder_manager = MailFolderManager(self.connector)

    def _save_config(self) -> None:
        config.save_config(self.config, str(self.config_path))

    def get_account_by_name(self, name: str) -> dict[str, Any] | None:
        """Finds an account by its friendly name, or returns the default."""
        for acc in self.accounts:
            if acc.get("friendly_name") == name:
                return acc
        
        return self.accounts[0] if name == "default" and self.accounts else None

