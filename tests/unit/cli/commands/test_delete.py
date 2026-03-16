import pytest
import argparse
from unittest.mock import MagicMock, patch, ANY
from cli.commands.delete import handle_delete

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('questionary.confirm')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_delete_success(mock_render, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        folder="INBOX",
        json=False
    )
    mock_confirm.return_value.ask.return_value = True
    mock_manager.deleter.delete_email.return_value = (True, "Deleted")
    
    handle_delete(args, mock_manager)
    
    # Verify deleter.delete_email was called
    mock_manager.deleter.delete_email.assert_called_once_with(mock_manager.accounts[0], "", "123", folder="INBOX")
    mock_render.assert_called_once_with(ANY, type="success", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_delete_account_not_found(mock_render, mock_manager):
    args = argparse.Namespace(account="non_existent", id="123", json=False)
    mock_manager.get_account_by_name.return_value = None
    
    handle_delete(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('questionary.confirm')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_delete_cancel(mock_render, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        folder="INBOX",
        json=False
    )
    mock_confirm.return_value.ask.return_value = False
    
    handle_delete(args, mock_manager)
    
    assert mock_manager.deleter.delete_email.call_count == 0

@patch('questionary.confirm')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_delete_failed(mock_render, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        folder="INBOX",
        json=False
    )
    mock_confirm.return_value.ask.return_value = True
    mock_manager.deleter.delete_email.return_value = (False, "Delete failed")
    
    handle_delete(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="warning", json_output=False)

@patch('questionary.confirm')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_delete_exception(mock_render, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        folder="INBOX",
        json=False
    )
    mock_confirm.return_value.ask.return_value = True
    mock_manager.deleter.delete_email.side_effect = Exception("Boom")
    
    handle_delete(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.commands.delete.config.get_verified_password')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_delete_password_cancel(mock_render, mock_get_pass, mock_manager):
    args = argparse.Namespace(account="test_acc", id="123", json=False)
    mock_manager.encryption_enabled = True
    mock_get_pass.side_effect = ValueError("cancelled")
    
    handle_delete(args, mock_manager)
    
    mock_get_pass.assert_called_once()
    mock_manager.deleter.delete_email.assert_not_called()
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('questionary.confirm')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_delete_success_json(mock_render, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        folder="INBOX",
        json=True
    )
    mock_confirm.return_value.ask.return_value = True
    mock_manager.deleter.delete_email.return_value = (True, "Deleted")
    
    handle_delete(args, mock_manager)
    
    # Verify deleter.delete_email was called
    mock_manager.deleter.delete_email.assert_called_once_with(mock_manager.accounts[0], "", "123", folder="INBOX")
    mock_render.assert_called_once_with(ANY, type="success", json_output=True)
