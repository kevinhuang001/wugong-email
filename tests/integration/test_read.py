import pytest
import json
from tests.conftest import run_wugong_command
from tests.test_utils import init_mailbox

def test_read_all_params(mail_server, mail_config):
    """Test the 'read' command with all available parameters."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    imap_port = mail_server["imap_port"]
    
    # Initialize mailbox for user1
    init_mailbox("user1", "password", imap_port)
    
    # Sync first so database is populated
    output = run_wugong_command(["sync", "user1"], config_path, password)
    res = json.loads(output)
    
    # Get ID of the one with an attachment (security updates)
    urgent_msg = next(m for m in res if "Urgent" in m.get("subject"))
    msg_id = urgent_msg.get("id")
    
    # read --account, --id, --folder, --raw, --browser
    # We test with --browser to ensure it doesn't crash.
    # We mock webbrowser.open to avoid actually opening a browser.
    from unittest.mock import patch
    with patch("webbrowser.open"):
        read_args = [
            "read", 
            "--account", "user1", 
            "--id", str(msg_id),
            "--folder", "INBOX",
            "--raw",
            "--browser",
            "--text"
        ]
        
        output = run_wugong_command(read_args, config_path, password)
        res = json.loads(output)
        
        assert "security updates" in res.get("content").lower()
    # If raw is requested, content might be encoded or structured differently.
    # We verify it doesn't fail.

def test_read_missing_account(mail_config):
    """Test read without account parameter (should use default)."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Run sync for default account (user1)
    run_wugong_command(["sync"], config_path, password)
    
    # Get IDs from list output for all accounts
    output = run_wugong_command(["list", "all"], config_path, password)
    res = json.loads(output)
    
    # Just read the first email from first account (user1)
    # Filter to ensure we get an ID from user1
    user1_emails = [m for m in res if m.get("account") == "user1" or not m.get("account")]
    msg_id = user1_emails[0].get("id")
    
    # read --id (should default to first account)
    output = run_wugong_command(["read", "--id", str(msg_id)], config_path, password)
    res = json.loads(output)
    
    assert str(res.get("id")) == str(msg_id)
    assert "subject" in res
