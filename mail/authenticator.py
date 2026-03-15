from typing import Any
import requests
from crypto_utils import decrypt_data, encrypt_data

class MailAuthenticator:
    def __init__(self, encryption_enabled: bool, salt: str):
        self.encryption_enabled = encryption_enabled
        self.salt = salt

    def decrypt_account_auth(self, account: dict[str, Any], password: str) -> dict[str, Any]:
        """Decrypts sensitive fields in the account's authentication details."""
        auth = account.get("auth", {})
        decrypted_auth = {}
        sensitive_keys = {"password", "client_id", "client_secret", "refresh_token", "access_token"}
        
        for k, v in auth.items():
            if self.encryption_enabled and k in sensitive_keys and isinstance(v, str) and v:
                try:
                    decrypted_auth[k] = decrypt_data(v, password, self.salt)
                except Exception as e:
                    raise Exception(f"Decryption failed for {k}: {e}")
            else:
                decrypted_auth[k] = v
        return decrypted_auth

    def refresh_oauth2_token(self, account: dict[str, Any], auth: dict[str, Any], password: str, config_obj: dict[str, Any]) -> str | None:
        """Refreshes the OAuth2 access token and updates config."""
        if not (refresh_token := auth.get("refresh_token")) or not (token_url := auth.get("token_url")):
            return None

        print(f"🔄 Refreshing OAuth2 token for '{account.get('friendly_name')}'...")
        
        payload = {
            'client_id': auth.get('client_id'),
            'client_secret': auth.get('client_secret'),
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': " ".join(auth.get('scopes') or [])
        }
        
        try:
            response = requests.post(token_url, data=payload, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            new_access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token', refresh_token)
            
            # Update the account in the config object
            for acc in config_obj.get("accounts", []):
                if acc.get("friendly_name") == account.get("friendly_name"):
                    auth_ref = acc.setdefault("auth", {})
                    if self.encryption_enabled:
                        auth_ref["access_token"] = encrypt_data(new_access_token, password, self.salt)
                        auth_ref["refresh_token"] = encrypt_data(new_refresh_token, password, self.salt)
                    else:
                        auth_ref["access_token"] = new_access_token
                        auth_ref["refresh_token"] = new_refresh_token
            return new_access_token
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
