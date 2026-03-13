import toml
import base64
import questionary
import os
from crypto_utils import decrypt_data
from mail import MailManager

def read_config():
    manager = MailManager()
    config = manager.config

    if not config or not config.get("accounts"):
        print(f"Error: Config not found or no accounts configured. Run wizard.py first.")
        return

    encryption_enabled = manager.encryption_enabled
    password = ""
    salt = manager.salt

    if encryption_enabled:
        password = questionary.password("Enter encryption password to decrypt accounts:").ask()
        if not password:
            print("Password is required for decryption.")
            return

    print("\n" + "="*40)
    print("      EMAIL ACCOUNTS CONFIGURATION")
    print("="*40)

    accounts = manager.accounts
    for idx, acc in enumerate(accounts, 1):
        print(f"\n[{idx}] Friendly Name: {acc.get('friendly_name')}")
        print(f"    Method: {acc.get('login_method')}")
        print(f"    IMAP: {acc.get('imap_server')}:{acc.get('imap_port')}")
        print(f"    SMTP: {acc.get('smtp_server')}:{acc.get('smtp_port')}")
        
        try:
            decrypted_auth = manager.auth_manager.decrypt_account_auth(acc, password)
            
            # Print auth details
            for k, v in decrypted_auth.items():
                # Mask long secrets for display
                display_val = v
                if k in ["password", "client_secret", "access_token", "refresh_token"] and v and len(str(v)) > 8:
                    display_val = str(v)[:8] + "********"
                print(f"    Auth {k}: {display_val}")
                
        except Exception as e:
            print(f"    [!] Failed to decrypt auth: {e}")

    print("\n" + "="*40)

if __name__ == "__main__":
    read_config()
