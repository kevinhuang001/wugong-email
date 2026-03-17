import pytest
import json
from tests.conftest import run_wugong_command

def test_account_add_all_params(mail_server, mail_config):
    """Test the 'account add' command with all available parameters."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    imap_port = mail_server["imap_port"]
    smtp_port = mail_server["smtp_port"]
    
    # account add --friendly-name, --provider, --login-method, --auth-method, 
    # --username, --imap-server, --imap-port, --imap-tls, 
    # --smtp-server, --smtp-port, --smtp-tls, --password, --sync-limit
    add_args = [
        "account", "add", 
        "--friendly-name", "full_param_user",
        "--provider", "other",
        "--login-method", "Password",
        "--username", "user1",
        "--imap-server", "127.0.0.1",
        "--imap-port", str(imap_port),
        "--imap-tls", "Plain",
        "--smtp-server", "127.0.0.1",
        "--smtp-port", str(smtp_port),
        "--smtp-tls", "Plain",
        "--password", "password",
        "--sync-limit", "50"
    ]
    
    output = run_wugong_command(add_args, config_path, password)
    res = json.loads(output)
    
    # Depending on implementation, 'res' may contain the added account or status
    assert any("full_param_user" in str(v) for v in res.values() if isinstance(v, str))


def test_account_list_json(mail_config):
    """Test 'account list' command with --json."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    output = run_wugong_command(["account", "list"], config_path, password)
    res = json.loads(output)
    
    assert isinstance(res, list)
    account_names = [acc.get("friendly_name") for acc in res]
    assert "user1" in account_names
    assert "user2" in account_names

def test_account_delete_priority(mail_config):
    """Test 'account delete' command prioritizes command-line arguments."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Verify account exists first
    output = run_wugong_command(["account", "list"], config_path, password)
    res = json.loads(output)
    assert any(acc.get("friendly_name") == "user2" for acc in res)
    
    # Delete user2 specifying it as argument
    output = run_wugong_command(["account", "delete", "-a", "user2"], config_path, password)
    res = json.loads(output)
    
    # Verify it was deleted
    output = run_wugong_command(["account", "list"], config_path, password)
    res = json.loads(output)
    assert not any(acc.get("friendly_name") == "user2" for acc in res)
