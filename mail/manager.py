import os
from .auth import AuthManager
from .storage import StorageManager
from .sender import MailSender
from .reader import MailReader
import config

class MailManager:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = config.get_config_path()
                
        self.config_path = config_path
        self.config = config.load_config(self.config_path)
        self.accounts = self.config.get("accounts", [])
        
        self.encryption_enabled = self.config.get("general", {}).get("encryption_enabled", False)
        self.encrypt_emails = self.config.get("general", {}).get("encrypt_emails", False)
        
        self.salt = config.get_salt(self.config)
        
        # Initialize sub-modules
        self.auth_manager = AuthManager(self.encryption_enabled, self.salt)
        
        db_path = os.path.join(os.path.dirname(self.config_path), "cache.db")
        self.storage_manager = StorageManager(db_path, self.encrypt_emails, self.encryption_enabled, self.salt)
        
        self.sender = MailSender(self.auth_manager, self.config, self._save_config)
        self.reader = MailReader(self.auth_manager, self.storage_manager, self.config, self._save_config)

    def _save_config(self):
        config.save_config(self.config, self.config_path)

    def get_account_by_name(self, name):
        # 1. First, look for an exact match by friendly_name
        for acc in self.accounts:
            if acc.get("friendly_name") == name:
                return acc
        
        # 2. If name is "default" and no account is explicitly named "default",
        # fall back to the first account in the list
        if name == "default" and self.accounts:
            return self.accounts[0]
            
        return None

