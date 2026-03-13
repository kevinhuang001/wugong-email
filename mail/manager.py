import os
import toml
from .auth import AuthManager
from .storage import StorageManager
from .sender import MailSender
from .reader import MailReader

class MailManager:
    def __init__(self, config_path=None):
        if config_path is None:
            # Default to ~/.wugong/config.toml if not provided
            config_path = os.path.join(os.path.expanduser("~"), ".wugong", "config.toml")
            # Fallback to local config.toml for development/testing if installation doesn't exist
            if not os.path.exists(config_path) and os.path.exists("config.toml"):
                config_path = "config.toml"
                
        self.config_path = config_path
        self.config = self._load_config()
        self.accounts = self.config.get("accounts", [])
        
        self.encryption_enabled = self.config.get("general", {}).get("encryption_enabled", False)
        self.encrypt_emails = self.config.get("general", {}).get("encrypt_emails", False)
        self.salt = self.config.get("general", {}).get("salt", "wugong-default-salt")
        
        # Initialize sub-modules
        self.auth_manager = AuthManager(self.encryption_enabled, self.salt)
        
        db_path = os.path.join(os.path.dirname(config_path), "cache.db")
        self.storage_manager = StorageManager(db_path, self.encrypt_emails, self.encryption_enabled, self.salt)
        
        self.sender = MailSender(self.auth_manager, self.config, self._save_config)
        self.reader = MailReader(self.auth_manager, self.storage_manager, self.config, self._save_config)

    def _load_config(self):
        if os.path.exists(self.config_path):
            return toml.load(self.config_path)
        return {"general": {}, "accounts": []}

    def _save_config(self):
        with open(self.config_path, "w") as f:
            toml.dump(self.config, f)

    def get_account_by_name(self, name):
        if name == "default" and self.accounts:
            return self.accounts[0]
        for acc in self.accounts:
            if acc.get("friendly_name") == name:
                return acc
        return None

