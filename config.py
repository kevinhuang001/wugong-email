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

def get_encryption_password(args: Optional[Any] = None, prompt_text: str = "Enter encryption password:", ignore_env: bool = False, non_interactive: Optional[bool] = None) -> Optional[str]:
    """
    Get encryption password from --encryption-password arg, WUGONG_PASSWORD env var, or interactive prompt.
    """
    # 1. Check CLI argument if provided (only if not ignore_env)
    if args and not ignore_env:
        # Check specifically for encryption_password
        password = getattr(args, "encryption_password", None)
        if password:
            logger.debug("Encryption password retrieved from CLI argument (encryption_password).")
            return password
    
    # 2. Check environment variable (only if not ignore_env)
    if not ignore_env:
        password = os.environ.get("WUGONG_PASSWORD")
        if password:
            logger.debug("Encryption password retrieved from environment variable.")
            return password
    
    # 3. Interactive prompt (only if not in non-interactive mode)
    if non_interactive is None:
        is_non_interactive = False
    else:
        is_non_interactive = non_interactive
    
    if is_non_interactive:
        return None

    # Force prompt
    try:
        from cli.render import CLIRenderer
        password = questionary.password(prompt_text, style=CLIRenderer.get_questionary_style()).ask()
        if password is None: # User cancelled with Ctrl+C
            raise KeyboardInterrupt
        return password
    except KeyboardInterrupt:
        return None
    except Exception:
        return None

def get_verified_password(config_data: Dict[str, Any], args: Optional[Any] = None, prompt_text: str = "Enter encryption password:", non_interactive: Optional[bool] = None) -> str:
    """Gets and verifies the encryption password with retries."""
    general = config_data.get("general", {})
    # Check if encryption is enabled in general settings
    encryption_enabled = general.get("encryption_enabled", False) or general.get("encrypt_emails", False)
    
    if not encryption_enabled:
        return ""

    if non_interactive is None:
        is_non_interactive = False
    else:
        is_non_interactive = non_interactive
    
    # In interactive mode, we allow up to 3 attempts
    max_attempts = 1 if is_non_interactive else 3
    
    for attempt in range(max_attempts):
        # 1. Get password
        # In the first attempt, we check everything. 
        # In subsequent attempts, we ignore env/args and force a prompt.
        password = get_encryption_password(args, prompt_text, ignore_env=True if attempt > 0 else False, non_interactive=is_non_interactive)
        
        if not password:
            if is_non_interactive:
                raise ValueError("Encryption password is REQUIRED in non-interactive mode (via --encryption-password or WUGONG_PASSWORD).")
            else:
                raise ValueError("Encryption password is required to proceed.")

        # 2. Verify password
        if verify_encryption_password(config_data, password):
            return password
        
        # 3. Handle failure
        if is_non_interactive:
            raise ValueError("Invalid encryption password. Make sure it matches the one used during 'init'.")
        else:
            from cli.render import CLIRenderer
            CLIRenderer.render_message(f"Invalid encryption password (attempt {attempt + 1}/{max_attempts}). Please try again.", type="error")
            # Clear the password from args to force prompt in next attempt if it came from args
            if args and hasattr(args, "encryption_password"):
                delattr(args, "encryption_password")
    
    raise ValueError("Invalid encryption password. Authentication failed after multiple attempts.")

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
            # logger.info(f"Configuration loaded from {path}")
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
    # logger.info(f"Configuration saved to {path}")
    logger.debug(f"Config saved to {path}. Accounts: {[a.get('friendly_name') for a in config.get('accounts', [])]}")

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
