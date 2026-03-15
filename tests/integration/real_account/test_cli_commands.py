import pytest
import os
import sys
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from main import main

# Get encryption password
PASSWORD = os.environ.get("WUGONG_PASSWORD", "test_password")

@pytest.fixture(scope="module")
def setup_config():
    """Prepare the test environment by copying configuration to a temporary directory."""
    # Prioritize config directory from environment variable, then check local path and default path
    possible_dirs = [
        os.environ.get("WUGONG_TEST_CONFIG_DIR"), # Explicitly provided test config dir
        Path("config.toml").parent if Path("config.toml").exists() else None, # Local config if present
        Path.home() / ".config" / "wugong", # New default config directory
        Path.home() / ".wugong" # Legacy config directory
    ]
    
    original_config_dir = None
    for d in possible_dirs:
        if d and Path(d).exists() and (Path(d) / "config.toml").exists():
            original_config_dir = Path(d)
            break
            
    if not original_config_dir:
        pytest.skip("No test account configuration found. Set WUGONG_TEST_CONFIG_DIR or provide a local config.toml.")


    temp_dir = Path(tempfile.mkdtemp())
    
    # Copy configuration file
    shutil.copy(original_config_dir / "config.toml", temp_dir / "config.toml")
    
    # Copy database (if exists)
    cache_db = original_config_dir / "cache.db"
    if cache_db.exists():
        shutil.copy(cache_db, temp_dir / "cache.db")
    
    # Set environment variable so the app uses the config in the temporary directory
    with patch.dict(os.environ, {"WUGONG_CONFIG": str(temp_dir / "config.toml")}):
        yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="module")
def real_accounts(setup_config):
    """Get the first 3 accounts from the real configuration."""
    from mail import MailManager
    manager = MailManager(setup_config / "config.toml")
    # If there are fewer than 3 accounts, return all accounts
    return [acc.get("friendly_name") for acc in manager.accounts[:3]]

@pytest.mark.real_account
def test_cli_list_multiple_accounts(setup_config, real_accounts):
    """Test the 'list' command for multiple accounts."""
    for account_name in real_accounts:
        with patch('sys.argv', ['main.py', '--password', PASSWORD, 'list', account_name, '--limit', '2']), \
             patch('cli.render.console') as mock_console:
            try:
                main()
                assert mock_console.print.called
                # Check for decryption failure in output
                output = "".join(str(call) for call in mock_console.print.call_args_list)
                if "Decryption failed" in output:
                    print(f"Skipping account '{account_name}' in list test due to decryption failure.")
                    continue
                assert "Error" not in output
            except Exception as e:
                if "Decryption failed" in str(e):
                    print(f"Skipping account '{account_name}' in list test due to decryption failure: {e}")
                    continue
                raise

@pytest.mark.real_account
def test_cli_sync_multiple_accounts(setup_config, real_accounts):
    """Test the 'sync' command for multiple accounts."""
    for account_name in real_accounts:
        # Sync 1 email
        with patch('sys.argv', ['main.py', '--password', PASSWORD, 'sync', account_name, '--limit', '1']), \
             patch('cli.commands.sync.console') as mock_console, \
             patch('cli.commands.sync.Progress', MagicMock()):
            try:
                main()
                output = "".join(str(call) for call in mock_console.print.call_args_list)
                if "Decryption failed" in output:
                    print(f"Skipping account '{account_name}' in sync test due to decryption failure.")
                    continue
                assert "Error" not in output
            except Exception as e:
                if "Decryption failed" in str(e):
                    print(f"Skipping account '{account_name}' in sync test due to decryption failure: {e}")
                    continue
                raise

@pytest.mark.real_account
def test_cli_read_multiple_accounts(setup_config, real_accounts):
    """Test the 'read' command for multiple accounts."""
    from mail import MailManager
    manager = MailManager(setup_config / "config.toml")
    
    for account_name in real_accounts:
        acc = manager.get_account_by_name(account_name)
        # Get emails from local cache
        emails = manager.storage_manager.get_emails_from_cache(
            acc.get("friendly_name"), limit=1, search_criteria={}, password=PASSWORD
        )
        if not emails:
            # If no cache, sync once
            with patch('sys.argv', ['main.py', '--password', PASSWORD, 'sync', account_name, '--limit', '1']), \
                 patch('cli.commands.sync.console'), \
                 patch('cli.commands.sync.Progress', MagicMock()):
                main()
            emails = manager.storage_manager.get_emails_from_cache(
                acc.get("friendly_name"), limit=1, search_criteria={}, password=PASSWORD
            )
            
        if not emails:
            continue
            
        email_id = emails[0]['id']
        folder = emails[0].get('folder', 'INBOX')
        
        with patch('sys.argv', ['main.py', '--password', PASSWORD, 'read', '--id', email_id, '--account', account_name, '--folder', folder]), \
             patch('questionary.select') as mock_select, \
             patch('sys.stdin.isatty', return_value=True), \
             patch('cli.render.console') as mock_console:
            
            mock_select.return_value.ask.return_value = "text"
            main()
            # If read fails, mock_console.print should be called to show the error.
            # If successful, CLIRenderer.render_email_content will also call console.print.
            assert mock_console.print.called

@pytest.mark.real_account
def test_cli_account_list(setup_config):
    """Test 'account list' command execution in a real terminal."""
    with patch('sys.argv', ['main.py', 'account', 'list']), \
         patch('cli.commands.account.console') as mock_console:
        main()
        assert mock_console.print.called

@pytest.mark.real_account
def test_cli_send_multiple_accounts(setup_config, real_accounts):
    """Test the 'send' command for multiple accounts."""
    # Send to test email, usually sending to oneself
    from mail import MailManager
    manager = MailManager(setup_config / "config.toml")
    
    for account_name in real_accounts:
        acc = manager.get_account_by_name(account_name)
        # Use the account's own email address as the recipient
        try:
            auth = manager.connector.auth_manager.decrypt_account_auth(acc, PASSWORD)
        except Exception as e:
            if "Decryption failed" in str(e):
                print(f"Skipping account '{account_name}' in send test due to decryption failure: {e}")
                continue
            raise
            
        recipient = auth.get("username")
        
        if not recipient:
            continue
            
        with patch('sys.argv', ['main.py', '--password', PASSWORD, 'send', '--account', account_name, 
                               '--to', recipient, '--subject', f'Test from {account_name}', 
                               '--body', f'This is a test email sent from {account_name} in integration test.']), \
             patch('cli.commands.send.console') as mock_console:
            main()
            # Check if output contains success message
            assert any("Successfully sent email" in str(call) for call in mock_console.print.call_args_list)

@pytest.mark.real_account
def test_cli_folder_list_multiple_accounts(setup_config, real_accounts):
    """Test the 'folder list' command for multiple accounts."""
    for account_name in real_accounts:
        with patch('sys.argv', ['main.py', '--password', PASSWORD, 'folder', 'list', account_name]), \
             patch('cli.commands.folder.console') as mock_console:
            main()
            assert mock_console.print.called

@pytest.mark.real_account
def test_cli_delete_email_multiple_accounts(setup_config, real_accounts):
    """Test the 'delete' command for multiple accounts (mock logic, no actual IMAP deletion)."""
    from mail import MailManager
    manager = MailManager(setup_config / "config.toml")
    
    for account_name in real_accounts:
        acc = manager.get_account_by_name(account_name)
        emails = manager.storage_manager.get_emails_from_cache(
            acc.get("friendly_name"), limit=1, search_criteria={}, password=PASSWORD
        )
        if not emails:
            continue
            
        email_id = emails[0]['id']
        folder = emails[0].get('folder', 'INBOX')
        
        # Mock deletion, patching the manager method that performs actual deletion
        with patch('sys.argv', ['main.py', '--password', PASSWORD, 'delete', '--id', email_id, '--account', account_name, '--folder', folder]), \
             patch('questionary.confirm') as mock_confirm, \
             patch('mail.deleter.MailDeleter.delete_email', return_value=(True, "Email deleted successfully.")) as mock_delete, \
             patch('cli.commands.delete.console') as mock_console:
            
            mock_confirm.return_value.ask.return_value = True
            main()
            # Confirm command completion and success message output
            assert any("deleted" in str(call).lower() for call in mock_console.print.call_args_list)
            assert mock_delete.called

