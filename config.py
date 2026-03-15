import os
import toml
import base64
import sys
import questionary
from pathlib import Path
from typing import Optional, Dict, Any, Union
from logger import logger

from crypto_utils import decrypt_data

def verify_encryption_password(config_data: Dict[str, Any], password: str) -> bool:
    """Verifies the encryption password against the canary or existing accounts."""
    general = config_data.get("general", {})
    if not (general.get("encryption_enabled") or general.get("encrypt_emails")):
        return True
    
    salt = get_salt(config_data)
    canary = general.get("canary")
    if canary:
        try:
            # Try to decrypt the canary value
            decrypted = decrypt_data(canary, password, salt)
            return decrypted == "wugong"
        except Exception:
            return False
            
    # Fallback for legacy configs without a canary: try to decrypt the first account
    accounts = config_data.get("accounts", [])
    if not accounts:
        # If no canary and no accounts, we can't verify yet, but it's likely a fresh init
        return True
        
    from mail.authenticator import MailAuthenticator
    auth_manager = MailAuthenticator(encryption_enabled=True, salt=salt)
    try:
        # Try to decrypt sensitive fields of the first account
        auth_manager.decrypt_account_auth(accounts[0], password)
        return True
    except Exception:
        return False

def get_encryption_password(args: Optional[Any] = None, prompt_text: str = "Enter encryption password:") -> Optional[str]:
    """
    Get encryption password from --encryption-password arg, WUGONG_PASSWORD env var, or interactive prompt.
    """
    # 1. Check CLI argument if provided
    if args:
        # Check specifically for encryption_password
        password = getattr(args, "encryption_password", None)
        if password:
            logger.debug("Encryption password retrieved from CLI argument (encryption_password).")
            return password
    
    # 2. Check environment variable
    password = os.environ.get("WUGONG_PASSWORD")
    if password:
        logger.debug("Encryption password retrieved from environment variable.")
        return password
    
    # 3. Interactive prompt (only if in a terminal AND not in non-interactive mode)
    is_non_interactive = getattr(args, "non_interactive", False) or not sys.stdin.isatty()
    
    if not is_non_interactive:
        logger.debug("Requesting encryption password via interactive prompt.")
        return questionary.password(prompt_text).ask()
    
    logger.warning("No encryption password found in CLI, env, or terminal (non-interactive mode enabled).")
    return None

def get_verified_password(config_data: Dict[str, Any], args: Optional[Any] = None, prompt_text: str = "Enter encryption password:") -> str:
    """
    Retrieves and verifies the encryption password.
    Raises ValueError if password is missing (in non-interactive mode) or invalid.
    """
    general = config_data.get("general", {})
    encryption_enabled = general.get("encryption_enabled", False) or general.get("encrypt_emails", False)
    
    if not encryption_enabled:
        return ""
    
    # 1. Get password
    password = get_encryption_password(args, prompt_text)
    
    # 2. Check if missing in non-interactive mode
    is_non_interactive = getattr(args, "non_interactive", False) or not sys.stdin.isatty()
    
    if not password:
        if is_non_interactive:
            raise ValueError("Encryption password is REQUIRED in non-interactive mode (via --encryption-password or WUGONG_PASSWORD).")
        else:
            # If interactive but user cancelled prompt
            raise ValueError("Encryption password is required to proceed.")
                
    # 3. Verify password
    if not verify_encryption_password(config_data, password):
        raise ValueError("Invalid encryption password. Make sure it matches the one used during 'init'.")
    
    return password

def get_config_path() -> Path:
    """Determine the configuration file path based on environment variables or defaults."""
    env_path = os.environ.get("WUGONG_CONFIG")
    if env_path:
        return Path(env_path)
    
    # Default path in ~/.config/wugong/config.toml
    default_path = Path.home() / ".config" / "wugong" / "config.toml"
    
    # Fallback to local config.toml if the default doesn't exist but local does
    local_path = Path("config.toml")
    if not default_path.exists() and local_path.exists():
        return local_path
        
    # Also check ~/.wugong for backward compatibility
    legacy_path = Path.home() / ".wugong" / "config.toml"
    if not default_path.exists() and legacy_path.exists():
        return legacy_path
        
    return default_path

def load_config(path: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    """Load configuration from the specified path or the default path."""
    if path is None:
        path = get_config_path()
    else:
        path = Path(path)
        
    if path.exists():
        try:
            config_data = toml.load(path)
            logger.info(f"Configuration loaded from {path}")
            return config_data
        except Exception as e:
            logger.error(f"Error loading config from {path}: {e}")
            return {"general": {}, "accounts": []}
            
    logger.debug(f"Configuration file not found at {path}")
    return {"general": {}, "accounts": []}

def save_config(config: Dict[str, Any], path: Optional[Union[Path, str]] = None) -> None:
    """Save the configuration to the specified path or the default path."""
    if path is None:
        path = get_config_path()
    else:
        path = Path(path)
        
    path.parent.mkdir(parents=True, exist_ok=True)
        
    with open(path, "w") as f:
        toml.dump(config, f)
    logger.info(f"Configuration saved to {path}")

def get_salt(config: Dict[str, Any]) -> bytes:
    """Retrieve and decode the salt from the configuration."""
    salt_raw = config.get("general", {}).get("salt", "")
    if not salt_raw:
        logger.debug("Using default salt.")
        return b"wugong-default-salt"
        
    try:
        decoded_salt = base64.b64decode(salt_raw)
        return decoded_salt
    except Exception as e:
        logger.warning(f"Failed to decode salt as base64: {e}. Falling back to raw bytes.")
        if isinstance(salt_raw, str):
            return salt_raw.encode()
        return salt_raw
