import pytest
import json
from tests.conftest import run_wugong_command
from tests.test_utils import init_mailbox

def test_send_all_params(mail_server, mail_config):
    """Test the 'send' command with all available parameters."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    imap_port = mail_server["imap_port"]
    
    # Initialize mailboxes
    init_mailbox("user1", "password", imap_port)
    init_mailbox("user2", "password", imap_port)
    
    # Sync so accounts are ready
    run_wugong_command(["sync", "-a", "user1", "--all"], config_path, password)
    run_wugong_command(["sync", "-a", "user2", "--all"], config_path, password)
    
    # send --account, --to, --subject, --body, --attach
    # Attachments require a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".txt") as tf:
        tf.write(b"Test attachment content")
        tf.flush()
        
        send_args = [
            "send", 
            "--account", "user1", 
            "--to", "user2", 
            "--subject", "Integration Test Send", 
            "--body", "Body of the email", 
            "--attach", tf.name
        ]
        
        output = run_wugong_command(send_args, config_path, password)
        print(f"DEBUG: send output: {output}")
        res = json.loads(output)
        
        assert res.get("status") == "success"
        
    # Verify user2 received it
    output = run_wugong_command(["sync", "-a", "user2", "--all"], config_path, password)
    res = json.loads(output)
    
    assert any("Integration Test Send" in m.get("subject") for m in res)

def test_send_to_friendly_name(mail_server, mail_config):
    """Test sending using friendly names for sender/recipient."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Sync accounts
    run_wugong_command(["sync", "-a", "all", "--all"], config_path, password)
    
    # send --account (friendly), --to (friendly)
    send_args = [
        "send", 
        "--account", "user1", 
        "--to", "user2", 
        "--subject", "Friendly Name Test", 
        "--body", "Testing user1 to user2 using names."
    ]
    
    output = run_wugong_command(send_args, config_path, password)
    res = json.loads(output)
    
    assert res.get("status") == "success"
    
    # Sync user2 to confirm
    output = run_wugong_command(["sync", "-a", "user2", "--all"], config_path, password)
    res = json.loads(output)
    assert any("Friendly Name Test" in m.get("subject") for m in res)
