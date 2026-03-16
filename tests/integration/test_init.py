import pytest
import json
import os
from unittest.mock import patch
from tests.conftest import run_wugong_command

def test_init_command_all_params(tmp_path):
    """Test the 'init' command with all available parameters."""
    config_dir = tmp_path / "init_test"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    password = "new_password"
    
    # All params: --encryption-password, --encrypt-creds, --encrypt-emails, 
    # --console-log-level, --file-log-level, --sync-interval
    init_args = [
        "init", 
        "--encryption-password", password, 
        "--encrypt-creds", 
        "--encrypt-emails", 
        "--console-log-level", "DEBUG", 
        "--file-log-level", "INFO",
        "--sync-interval", "15"
    ]
    
    # We use a custom environment variable for config path
    with patch.dict(os.environ, {"WUGONG_CONFIG": str(config_file)}):
        output = run_wugong_command(init_args, config_file, password)
        res = json.loads(output)
        assert res.get("status") == "success"
        
    # Verify config content
    import toml
    with open(config_file, "r") as f:
        config_data = toml.load(f)
        
    assert config_data["general"]["encryption_enabled"] is True
    assert config_data["general"]["encrypt_emails"] is True
    assert config_data["general"]["console_log_level"] == "DEBUG"
    assert config_data["general"]["file_log_level"] == "INFO"
    assert config_data["general"]["sync_interval"] == 15
    assert "salt" in config_data["general"]

def test_init_no_encryption(tmp_path):
    """Test init with encryption disabled."""
    config_file = tmp_path / "no_encrypt.toml"
    password = "test"
    
    init_args = [
        "init",
        "--encryption-password", password,
        "--no-encrypt-creds",
        "--no-encrypt-emails"
    ]
    
    output = run_wugong_command(init_args, config_file, password)
    res = json.loads(output)
    assert res.get("status") == "success"
    
    import toml
    with open(config_file, "r") as f:
        config_data = toml.load(f)
    
    assert config_data["general"].get("encryption_enabled") is False
    assert config_data["general"].get("encrypt_emails") is False
