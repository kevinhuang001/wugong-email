import pytest
import argparse
from unittest.mock import MagicMock, patch
from cli.commands.sync import handle_sync

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.commands.sync.console')
def test_handle_sync_success(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX"
    )
    mock_manager.syncer.sync_emails.return_value = ([], {})
    
    handle_sync(args, mock_manager)
    
    # Verify syncer.sync_emails was called
    mock_manager.syncer.sync_emails.assert_called_once()
    assert mock_console.print.called

@patch('cli.commands.sync.console')
def test_handle_sync_account_not_found(mock_console, mock_manager):
    args = argparse.Namespace(account="non_existent", limit=20, all=False, password="test_password", folder="INBOX")
    mock_manager.get_account_by_name.return_value = None
    
    handle_sync(args, mock_manager)
    
    assert any("not found" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.sync.console')
def test_handle_sync_all_accounts(mock_console, mock_manager):
    args = argparse.Namespace(
        account="all",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX"
    )
    mock_manager.accounts = [
        {"friendly_name": "acc1"},
        {"friendly_name": "acc2"}
    ]
    mock_manager.syncer.sync_emails.return_value = ([], {})
    
    handle_sync(args, mock_manager)
    
    assert mock_manager.syncer.sync_emails.call_count == 2

@patch('cli.commands.sync.console')
def test_handle_sync_offline_failure(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX"
    )
    mock_manager.syncer.sync_emails.return_value = ([], {"is_offline": True, "error": "Connection Timeout"})
    
    handle_sync(args, mock_manager)
    
    assert any("sync failed" in str(call).lower() for call in mock_console.print.call_args_list)
    assert any("connection timeout" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.sync.console')
def test_handle_sync_with_progress_callback(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX"
    )
    mock_manager.syncer.sync_emails.return_value = ([], {"new_emails": [1, 2, 3]})
    
    # We want to verify progress_callback is called during sync
    # This is tricky because it's passed into sync_emails
    handle_sync(args, mock_manager)
    
    assert mock_manager.syncer.sync_emails.called
    callback = mock_manager.syncer.sync_emails.call_args[1]['progress_callback']
    assert callable(callback)
    
    # Trigger callback and ensure it doesn't crash (testing the closure)
    with patch('sys.stdin.isatty', return_value=True):
        callback(1, 10, "testing")

@patch('cli.commands.sync.config.get_encryption_password')
@patch('cli.commands.sync.console')
def test_handle_sync_password_cancel(mock_console, mock_get_pass, mock_manager):
    args = argparse.Namespace(account="test_acc", limit=20, all=False, folder="INBOX")
    mock_manager.encryption_enabled = True
    mock_get_pass.return_value = None
    
    handle_sync(args, mock_manager)
    
    mock_get_pass.assert_called_once()
    mock_manager.syncer.sync_emails.assert_not_called()

@patch('cli.commands.sync.console')
def test_handle_sync_no_accounts(mock_console, mock_manager):
    args = argparse.Namespace(account=None, limit=20, all=False, folder="INBOX")
    mock_manager.accounts = []
    
    handle_sync(args, mock_manager)
    
    assert any("no accounts configured" in str(call).lower() for call in mock_console.print.call_args_list)
