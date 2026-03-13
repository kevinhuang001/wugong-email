import imaplib
import smtplib
import base64
import requests
from crypto_utils import decrypt_data, encrypt_data

class AuthManager:
    def __init__(self, encryption_enabled, salt):
        self.encryption_enabled = encryption_enabled
        self.salt = salt

    def decrypt_account_auth(self, account, password):
        auth = account.get("auth", {})
        decrypted_auth = {}
        sensitive_keys = ["password", "client_id", "client_secret", "refresh_token", "access_token"]
        
        for k, v in auth.items():
            if self.encryption_enabled and k in sensitive_keys and isinstance(v, str) and v:
                try:
                    decrypted_auth[k] = decrypt_data(v, password, self.salt)
                except Exception as e:
                    raise Exception(f"Decryption failed for {k}: {e}")
            else:
                decrypted_auth[k] = v
        return decrypted_auth

    def refresh_oauth2_token(self, account, auth, password, config):
        """Refreshes the OAuth2 access token and updates config."""
        refresh_token = auth.get("refresh_token")
        token_url = auth.get("token_url")
        if not refresh_token or not token_url:
            return None

        print(f"🔄 Refreshing OAuth2 token for '{account.get('friendly_name')}'...")
        
        scopes = auth.get('scopes')
        if scopes is None:
            scopes = []
            
        payload = {
            'client_id': auth.get('client_id'),
            'client_secret': auth.get('client_secret'),
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': " ".join(scopes)
        }
        
        try:
            response = requests.post(token_url, data=payload)
            response.raise_for_status()
            token_data = response.json()
            
            new_access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token', refresh_token)
            
            # Update the account in the config object
            for acc in config.get("accounts", []):
                if acc.get("friendly_name") == account.get("friendly_name"):
                    if self.encryption_enabled:
                        acc["auth"]["access_token"] = encrypt_data(new_access_token, password, self.salt)
                        acc["auth"]["refresh_token"] = encrypt_data(new_refresh_token, password, self.salt)
                    else:
                        acc["auth"]["access_token"] = new_access_token
                        acc["auth"]["refresh_token"] = new_refresh_token
            return new_access_token
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
