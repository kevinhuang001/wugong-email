import os
import toml
import base64

def get_config_path():
    """Determine the configuration file path based on environment variables or defaults."""
    env_path = os.environ.get("WUGONG_CONFIG")
    if env_path:
        return env_path
    
    # Default path in ~/.wugong/config.toml
    default_path = os.path.join(os.path.expanduser("~"), ".wugong", "config.toml")
    
    # Fallback to local config.toml if the default doesn't exist but local does
    if not os.path.exists(default_path) and os.path.exists("config.toml"):
        return "config.toml"
        
    return default_path

def load_config(path=None):
    """Load configuration from the specified path or the default path."""
    if path is None:
        path = get_config_path()
        
    if os.path.exists(path):
        try:
            return toml.load(path)
        except Exception as e:
            print(f"Error loading config from {path}: {e}")
            return {"general": {}, "accounts": []}
    return {"general": {}, "accounts": []}

def save_config(config, path=None):
    """Save the configuration to the specified path or the default path."""
    if path is None:
        path = get_config_path()
        
    config_dir = os.path.dirname(path)
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
        
    with open(path, "w") as f:
        toml.dump(config, f)

def get_salt(config):
    """Retrieve and decode the salt from the configuration."""
    salt_raw = config.get("general", {}).get("salt", "")
    if not salt_raw:
        return b"wugong-default-salt"
        
    try:
        return base64.b64decode(salt_raw)
    except Exception:
        if isinstance(salt_raw, str):
            return salt_raw.encode()
        return salt_raw
