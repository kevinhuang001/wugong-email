import pytest
import json
from tests.conftest import run_wugong_command
from tests.test_utils import init_mailbox

def test_sync_all_params(mail_server, mail_config):
    """Test the 'sync' command with all available parameters."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    imap_port = mail_server["imap_port"]
    
    # Initialize mailboxes
    init_mailbox("user1", "password", imap_port)
    
    # sync -a <account> --folder, --limit, --all
    sync_args = [
        "sync", "-a", "user1", 
        "--folder", "Archive",
        "--limit", "10",
        "--all"
    ]
    
    output = run_wugong_command(sync_args, config_path, password)
    res = json.loads(output)
    
    # Archive has 3 seeded emails by default in init_mailbox
    assert len(res) == 3
    assert any("Old Receipt" in m.get("subject") for m in res)

def test_sync_no_account(mail_config):
    """Test sync without account (should sync all accounts if implemented, or default)."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Running sync with -a all --all to sync all accounts and all emails
    output = run_wugong_command(["sync", "-a", "all", "--all"], config_path, password)
    res = json.loads(output)
    
    # Should sync all configured accounts (user1, user2)
    # INBOX has 5 emails each in init_mailbox
    assert len(res) >= 10 # 5 from user1, 5 from user2
    
    # Check if results are grouped or combined
    if isinstance(res, list):
        assert len(res) >= 10
    elif isinstance(res, dict):
        assert "user1" in res
        assert "user2" in res
