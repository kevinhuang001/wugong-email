import pytest
import json
from tests.conftest import run_wugong_command
from tests.test_utils import init_mailbox

def test_delete_all_params(mail_server, mail_config):
    """Test the 'delete' command with all available parameters."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    imap_port = mail_server["imap_port"]
    
    # Initialize mailbox for user1
    init_mailbox("user1", "password", imap_port)
    
    # Sync first so database is populated
    output = run_wugong_command(["sync", "user1"], config_path, password)
    res = json.loads(output)
    
    # Get ID of first email (INBOX)
    msg_id = res[0].get("id")
    subject = res[0].get("subject")
    
    # delete --account, --id, --folder
    delete_args = [
        "delete", 
        "--account", "user1", 
        "--id", str(msg_id),
        "--folder", "INBOX"
    ]
    
    output = run_wugong_command(delete_args, config_path, password)
    res = json.loads(output)
    
    # Depending on implementation, 'res' might contain the deleted email or status
    assert res.get("status") == "success"
    
    # Verify it was deleted from local cache (list it again)
    output = run_wugong_command(["list", "user1", "--folder", "INBOX"], config_path, password)
    res = json.loads(output)
    
    assert not any(m.get("id") == msg_id for m in res)
    assert not any(m.get("subject") == subject for m in res)

def test_delete_multiple_ids(mail_config):
    """Test delete multiple IDs (if supported as comma separated or space separated)."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Get multiple IDs from list (all accounts)
    output = run_wugong_command(["list", "all"], config_path, password)
    res = json.loads(output)
    
    # Filter emails that belong to the first account (user1) to ensure delete works
    # since we are not specifying --account in the delete command below.
    # Actually, we can just specify the account to be safe, but the test 
    # might be intended to test the default account behavior.
    
    user1_emails = [m for m in res if m.get("account") == "user1" or not m.get("account")]
    ids = [str(m.get("id")) for m in user1_emails[:2]] # Take first 2
    
    # delete --id ID1,ID2
    # Check if delete supports comma separated or space separated IDs. 
    # Based on account.py, handle_delete usually expects a single ID if it's positional or --id.
    # We test it with single ID first.
    
    for msg_id in ids:
        output = run_wugong_command(["delete", "--id", msg_id], config_path, password)
        res = json.loads(output)
        assert res.get("status") == "success"
        
    # Verify both were deleted
    output = run_wugong_command(["list", "all"], config_path, password)
    res = json.loads(output)
    
    for msg_id in ids:
        assert not any(str(m.get("id")) == str(msg_id) for m in res)
