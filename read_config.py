import toml
import base64
import questionary
import os
from crypto_utils import decrypt_data

CONFIG_FILE = "config.toml"

def read_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Run wizard.py first.")
        return

    try:
        with open(CONFIG_FILE, "r") as f:
            config = toml.load(f)
    except Exception as e:
        print(f"Error reading TOML: {e}")
        return

    encryption_enabled = config.get("general", {}).get("encryption_enabled", False)
    password = ""
    salt = None

    if encryption_enabled:
        password = questionary.password("Enter encryption password to decrypt accounts:").ask()
        if not password:
            print("Password is required for decryption.")
            return
        salt_str = config.get("general", {}).get("salt", "")
        if salt_str:
            salt = base64.b64decode(salt_str)

    print("\n" + "="*40)
    print("      EMAIL ACCOUNTS CONFIGURATION")
    print("="*40)

    accounts = config.get("accounts", [])
    if not accounts:
        print("No accounts configured.")
        return

    for idx, acc in enumerate(accounts, 1):
        print(f"\n[{idx}] Friendly Name: {acc.get('friendly_name')}")
        print(f"    Method: {acc.get('login_method')}")
        print(f"    IMAP: {acc.get('imap_server')}:{acc.get('imap_port')}")
        print(f"    SMTP: {acc.get('smtp_server')}:{acc.get('smtp_port')}")
        
        auth = acc.get("auth", {})
        decrypted_auth = {}
        
        try:
            if encryption_enabled and salt:
                # Sensitive fields to decrypt
                sensitive_keys = ["password", "client_id", "client_secret", "refresh_token", "access_token"]
                for key, value in auth.items():
                    if key in sensitive_keys and value:
                        decrypted_auth[key] = decrypt_data(value, password, salt)
                    else:
                        decrypted_auth[key] = value
            else:
                decrypted_auth = auth
            
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
