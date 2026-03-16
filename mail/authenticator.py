import logging
from typing import Any
import requests
from requests_oauthlib import OAuth2Session
from crypto_utils import decrypt_data, encrypt_data, is_fernet_token
import oauth2

logger = logging.getLogger("wugong.mail.authenticator")

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
                if is_fernet_token(v):
                    try:
                        decrypted_auth[k] = decrypt_data(v, password, self.salt)
                    except Exception as e:
                        # Only raise if it's supposed to be encrypted but failed
                        # If the password was just wrong, Fernet should raise InvalidToken
                        logger.error(f"Decryption failed for {k}: {e}")
                        raise Exception(f"Decryption failed for {k}")
                else:
                    # Not a Fernet token, assume plain text but log a warning if encryption is enabled
                    # This handles the case where encryption was enabled later.
                    logger.debug(f"Field {k} is not encrypted, using as plain text.")
                    decrypted_auth[k] = v
            else:
                decrypted_auth[k] = v
        return decrypted_auth

    def refresh_oauth2_token(self, account: dict[str, Any], password: str) -> dict[str, Any] | None:
        """Refreshes the OAuth2 access token. Returns new auth dict if successful."""
        auth = account.get("auth", {})
        if not (refresh_token := auth.get("refresh_token")) or not (token_url := auth.get("token_url")):
            logger.error("Missing refresh_token or token_url for OAuth2 refresh.")
            return None

        # Decrypt refresh_token if encrypted
        if self.encryption_enabled and refresh_token and is_fernet_token(refresh_token):
            try:
                refresh_token = decrypt_data(refresh_token, password, self.salt)
            except Exception as e:
                logger.error(f"Failed to decrypt refresh_token: {e}")
                return None

        # Decrypt client_id and client_secret if encrypted
        client_id = auth.get("client_id")
        client_secret = auth.get("client_secret")
        if self.encryption_enabled:
            try:
                if client_id and is_fernet_token(client_id): 
                    client_id = decrypt_data(client_id, password, self.salt)
                if client_secret and is_fernet_token(client_secret): 
                    client_secret = decrypt_data(client_secret, password, self.salt)
            except Exception as e:
                logger.error(f"Failed to decrypt client credentials: {e}")
                return None

        logger.info(f"🔄 Refreshing OAuth2 token for '{account.get('friendly_name')}'...")
        
        try:
            session = OAuth2Session(
                client_id=client_id,
                scope=auth.get('scopes') or [],
                redirect_uri=auth.get('redirect_uri')
            )
            
            token = session.refresh_token(
                token_url,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret
            )
            
            new_access_token = token.get('access_token')
            new_refresh_token = token.get('refresh_token', refresh_token)
            
            # Return new tokens (encrypted if needed)
            new_auth = auth.copy()
            if self.encryption_enabled:
                new_auth["access_token"] = encrypt_data(new_access_token, password, self.salt)
                new_auth["refresh_token"] = encrypt_data(new_refresh_token, password, self.salt)
            else:
                new_auth["access_token"] = new_access_token
                new_auth["refresh_token"] = new_refresh_token
            
            logger.info("✅ Token refreshed successfully.")
            return new_auth
        except Exception as e:
            logger.error(f"⚠️ Error refreshing token: {e}")
            # If the error suggests the token is invalid/revoked, we should clear it
            error_msg = str(e).lower()
            if "invalid_grant" in error_msg or "expired" in error_msg or "revoked" in error_msg:
                logger.warning("🧹 Refresh token seems invalid, clearing it to force re-authorization.")
                new_auth = auth.copy()
                new_auth["refresh_token"] = ""
                new_auth["access_token"] = ""
                return new_auth
            return None

    def reauthorize_oauth2(self, account: dict[str, Any], password: str) -> dict[str, Any] | None:
        """Starts a full OAuth2 re-authorization flow if refresh fails."""
        auth = account.get("auth", {})
        
        # Decrypt client credentials if encrypted
        client_id = auth.get("client_id")
        client_secret = auth.get("client_secret")
        if self.encryption_enabled:
            try:
                if client_id and is_fernet_token(client_id): 
                    client_id = decrypt_data(client_id, password, self.salt)
                if client_secret and is_fernet_token(client_secret): 
                    client_secret = decrypt_data(client_secret, password, self.salt)
            except Exception as e:
                logger.error(f"Failed to decrypt client credentials for re-auth: {e}")
                return None

        logger.warning(f"🔄 Re-authorizing account '{account.get('friendly_name')}'...")
        
        try:
            token_data = oauth2.start_oauth_flow(
                client_id=client_id,
                client_secret=client_secret,
                auth_url=auth.get("auth_url"),
                token_url=auth.get("token_url"),
                scopes=auth.get("scopes", []),
                redirect_uri=auth.get("redirect_uri")
            )
            
            if not token_data or not (token := token_data.get('token')):
                logger.error("❌ Re-authorization failed: No token received.")
                return None
                
            new_access_token = token.get('access_token')
            new_refresh_token = token.get('refresh_token', '')
            
            new_auth = auth.copy()
            # Update detected email if needed
            if (detected_email := token_data.get('user_email')):
                new_auth["username"] = detected_email
            
            if self.encryption_enabled:
                new_auth["access_token"] = encrypt_data(new_access_token, password, self.salt)
                new_auth["refresh_token"] = encrypt_data(new_refresh_token, password, self.salt)
            else:
                new_auth["access_token"] = new_access_token
                new_auth["refresh_token"] = new_refresh_token
                
            logger.info("✅ Re-authorization successful.")
            return new_auth
        except Exception as e:
            logger.error(f"❌ Re-authorization error: {e}")
            return None
