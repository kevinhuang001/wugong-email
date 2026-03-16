import pytest
import json
from tests.conftest import run_wugong_command
from tests.test_utils import init_mailbox

def test_folder_list_all_params(mail_server, mail_config):
    """Test the 'folder list' command with all available parameters."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    imap_port = mail_server["imap_port"]
    
    # Initialize mailbox for user1
    init_mailbox("user1", "password", imap_port)
    
    # folder list <account>
    folder_args = [
        "folder", "list", "user1"
    ]
    
    output = run_wugong_command(folder_args, config_path, password)
    res = json.loads(output)
    
    # Should list all folders (INBOX, Archive, Travel, Shopping, Personal, draft, sent, trash, junk)
    folder_names = [f.get("name") for f in res]
    assert "INBOX" in folder_names
    assert "Archive" in folder_names
    assert "Travel" in folder_names
    assert "Shopping" in folder_names

def test_folder_create_and_delete(mail_server, mail_config):
    """Test folder create and delete commands."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # folder create --account <account> <name>
    create_args = [
        "folder", "create", 
        "--account", "user1", 
        "NewFolder"
    ]
    
    output = run_wugong_command(create_args, config_path, password)
    res = json.loads(output)
    
    assert res.get("status") == "success"
    
    # Verify it exists
    output = run_wugong_command(["folder", "list", "user1"], config_path, password)
    res = json.loads(output)
    assert any(f.get("name") == "NewFolder" for f in res)
    
    # folder delete --account <account> <name>
    delete_args = [
        "folder", "delete", 
        "--account", "user1", 
        "NewFolder"
    ]
    
    output = run_wugong_command(delete_args, config_path, password)
    res = json.loads(output)
    
    assert res.get("status") == "success"
    
    # Verify it was deleted
    output = run_wugong_command(["folder", "list", "user1"], config_path, password)
    res = json.loads(output)
    assert not any(f.get("name") == "NewFolder" for f in res)

def test_folder_move_email(mail_server, mail_config):
    """Test folder move email command."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Sync INBOX first
    output = run_wugong_command(["sync", "user1"], config_path, password)
    res = json.loads(output)
    
    # Get ID of first email in INBOX
    msg_id = res[0].get("id")
    subject = res[0].get("subject")
    
    # folder move <id> <dest> --account --src
    move_args = [
        "folder", "move", str(msg_id), "Archive",
        "--account", "user1",
        "--src", "INBOX"
    ]
    
    output = run_wugong_command(move_args, config_path, password)
    res = json.loads(output)
    
    assert res.get("status") == "success"
    
    # Verify it moved to Archive
    # First sync Archive to update local cache
    run_wugong_command(["sync", "user1", "--folder", "Archive"], config_path, password)
    
    output = run_wugong_command(["list", "user1", "--folder", "Archive"], config_path, password)
    res = json.loads(output)
    
    assert any(m.get("subject") == subject for m in res)
    
    # Verify it's no longer in INBOX
    output = run_wugong_command(["list", "user1", "--folder", "INBOX"], config_path, password)
    res = json.loads(output)
    assert not any(m.get("subject") == subject for m in res)
