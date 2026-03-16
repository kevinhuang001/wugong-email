import pytest
import json
import toml
from tests.conftest import run_wugong_command

def test_configure_all_params(mail_config):
    """Test the 'configure' command with all available parameters."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # configure --console-log-level, --file-log-level, --sync-interval
    configure_args = [
        "configure",
        "--console-log-level", "ERROR",
        "--file-log-level", "DEBUG",
        "--sync-interval", "30"
    ]
    
    output = run_wugong_command(configure_args, config_path, password)
    res = json.loads(output)
    
    assert res.get("status") == "success"
    
    # Verify config content
    with open(config_path, "r") as f:
        config_data = toml.load(f)
        
    assert config_data["general"]["console_log_level"] == "ERROR"
    assert config_data["general"]["file_log_level"] == "DEBUG"
    assert config_data["general"]["sync_interval"] == 30
