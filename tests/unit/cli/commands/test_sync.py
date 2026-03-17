import pytest
import argparse
from unittest.mock import MagicMock, patch, ANY
from cli.commands.sync import handle_sync

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.side_effect = lambda name: manager.accounts[0] if name == "test_acc" else None
    manager.encryption_enabled = False
    manager.non_interactive = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.render.CLIRenderer.render_message')
@patch('cli.render.CLIRenderer.render_email_table')
def test_handle_sync_success(mock_table, mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX",
        json=False
    )
    mock_manager.syncer.sync_emails.return_value = ([], {"new_emails": []})
    
    handle_sync(args, mock_manager)
    
    # Verify syncer.sync_emails was called
    mock_manager.syncer.sync_emails.assert_called_once()
    mock_render.assert_called_with(ANY, type="success")

@patch('cli.render.CLIRenderer.render_message')
@patch('cli.render.CLIRenderer.render_email_table')
def test_handle_sync_success_json(mock_table, mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX",
        json=True
    )
    mock_manager.syncer.sync_emails.return_value = ([], {"new_emails": []})
    
    handle_sync(args, mock_manager)
    
    # Verify syncer.sync_emails was called
    mock_manager.syncer.sync_emails.assert_called_once()
    mock_table.assert_called_once_with(ANY, show_folder=True, json_output=True, data=None)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_sync_account_not_found(mock_render, mock_manager):
    args = argparse.Namespace(account="non_existent", limit=20, all=False, password="test_password", folder="INBOX", json=False)
    mock_manager.get_account_by_name.return_value = None
    
    handle_sync(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_sync_account_not_found_json(mock_render, mock_manager):
    args = argparse.Namespace(account="non_existent", limit=20, all=False, password="test_password", folder="INBOX", json=True)
    mock_manager.get_account_by_name.return_value = None
    
    handle_sync(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=True)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_sync_all_accounts(mock_render, mock_manager):
    args = argparse.Namespace(
        account="all",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX",
        json=False
    )
    mock_manager.accounts = [
        {"friendly_name": "acc1"},
        {"friendly_name": "acc2"}
    ]
    mock_manager.syncer.sync_emails.return_value = ([], {"new_emails": []})
    
    handle_sync(args, mock_manager)
    
    assert mock_manager.syncer.sync_emails.call_count == 2

@patch('cli.render.CLIRenderer.render_message')
def test_handle_sync_offline_failure(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX",
        json=False
    )
    mock_manager.syncer.sync_emails.return_value = ([], {"is_offline": True, "error": "Connection Timeout"})
    
    handle_sync(args, mock_manager)
    
    mock_render.assert_called_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
@patch('cli.render.CLIRenderer.render_email_table')
def test_handle_sync_offline_failure_json(mock_table, mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX",
        json=True
    )
    mock_manager.syncer.sync_emails.return_value = ([], {"is_offline": True, "error": "Connection Timeout"})
    
    handle_sync(args, mock_manager)
    
    # Should call render_message with the error summary because all_emails is empty
    mock_render.assert_called_with(ANY, type="error", data={'errors': [{'account': 'test_acc', 'error': 'Connection Timeout', 'offline': True}]}, json_output=True)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_sync_with_progress_callback(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        limit=20,
        all=False,
        password="test_password",
        folder="INBOX",
        json=False
    )
    mock_manager.syncer.sync_emails.return_value = ([], {"new_emails": [1, 2, 3]})
    
    handle_sync(args, mock_manager)
    
    assert mock_manager.syncer.sync_emails.called
    callback = mock_manager.syncer.sync_emails.call_args[1]['progress_callback']
    assert callable(callback)
    
    # Trigger callback and ensure it doesn't crash
    with patch('sys.stdin.isatty', return_value=True):
        callback(1, 10, "testing")

@patch('cli.commands.sync.config.get_verified_password')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_sync_password_cancel(mock_render, mock_get_pass, mock_manager):
    args = argparse.Namespace(account="test_acc", limit=20, all=False, folder="INBOX", json=False)
    mock_manager.encryption_enabled = True
    mock_get_pass.side_effect = ValueError("cancelled")
    
    handle_sync(args, mock_manager)
    
    mock_get_pass.assert_called_once()
    mock_manager.syncer.sync_emails.assert_not_called()
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_sync_no_accounts(mock_render, mock_manager):
    args = argparse.Namespace(account=None, limit=20, all=False, folder="INBOX", json=False)
    mock_manager.accounts = []
    
    handle_sync(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="warning", json_output=False)

