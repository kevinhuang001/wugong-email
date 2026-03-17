import pytest
import json
from tests.conftest import run_wugong_command
from tests.test_utils import init_mailbox

def test_list_all_params(mail_server, mail_config):
    """Test the 'list' command with all available parameters."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    imap_port = mail_server["imap_port"]
    
    # Initialize mailbox for user1
    init_mailbox("user1", "password", imap_port)
    
    # Sync first so database is populated
    run_wugong_command(["sync", "-a", "user1"], config_path, password)
    run_wugong_command(["sync", "-a", "user1", "--folder", "Archive"], config_path, password)
    
    # list -a <account> --folder, --keyword, --from-user, --since, --before, --verbose, --local
    list_args = [
        "list", "-a", "user1", 
        "--folder", "Archive",
        "--keyword", "Old",
        "--from-user", "receipts@coffeeshop.com", # Matching seed data
        "--since", "01-Jan-2024",
        "--verbose",
        "--local"
    ]
    
    output = run_wugong_command(list_args, config_path, password)
    res = json.loads(output)
    
    # "Old Receipt" should match and is unread by default in seed
    assert len(res) == 1
    assert "Old Receipt" in res[0].get("subject")

def test_list_search_across_folders(mail_server, mail_config):
    """Test 'list' keyword search across all folders in local database."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Sync multiple folders
    run_wugong_command(["sync", "-a", "user1", "--folder", "Travel"], config_path, password)
    run_wugong_command(["sync", "-a", "user1", "--folder", "Shopping"], config_path, password)
    
    # Search across all folders using keyword
    output = run_wugong_command(["list", "-a", "user1", "--keyword", "Hotel"], config_path, password)
    res = json.loads(output)
    
    assert len(res) == 1
    assert "Hotel Reservation" in res[0].get("subject")
    assert res[0].get("folder") == "Travel"

def test_list_all_accounts(mail_config):
    """Test account list command."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Running account list
    output = run_wugong_command(["account", "list"], config_path, password)
    res = json.loads(output)
    
    # Should list all accounts (user1, user2)
    assert isinstance(res, list)
    account_names = [acc.get("friendly_name") for acc in res]
    assert "user1" in account_names
    assert "user2" in account_names

def test_list_default_account(mail_server, mail_config):
    """Test list without account (defaults to 'default' which is 'user1' in tests)."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Sync user1
    run_wugong_command(["sync", "-a", "user1", "--all"], config_path, password)
    
    # Running list without -a (should default to user1)
    output = run_wugong_command(["list"], config_path, password)
    res = json.loads(output)
    
    # Should return emails for user1
    assert isinstance(res, list)
    assert len(res) > 0
    # user1 is the first account added, so it should be the default
    assert any("Welcome" in m.get("subject") for m in res)
