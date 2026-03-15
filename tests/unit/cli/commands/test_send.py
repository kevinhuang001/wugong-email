import pytest
import argparse
from unittest.mock import MagicMock, patch
from cli.commands.send import handle_send

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.commands.send.console')
def test_handle_send_success(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body="Test Body",
        attach=None
    )
    # Correct mock for sender.send_email
    mock_manager.sender.send_email.return_value = (True, "Sent")
    
    handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_called_once()
    assert mock_console.print.called

@patch('cli.commands.send.console')
def test_handle_send_account_not_found(mock_console, mock_manager):
    args = argparse.Namespace(account="non_existent", to="to@test.com", subject="sub", body="body", attach=None)
    mock_manager.get_account_by_name.return_value = None
    
    handle_send(args, mock_manager)
    
    assert any("not found" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('questionary.text')
@patch('cli.commands.send.console')
def test_handle_send_interactive_body(mock_console, mock_text, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body=None,
        attach=None
    )
    mock_text.return_value.ask.return_value = "Interactive Body"
    mock_manager.sender.send_email.return_value = (True, "Sent")
    
    handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_called_once()
    assert "Interactive Body" in mock_manager.sender.send_email.call_args[1]['body']

@patch('cli.commands.send.console')
def test_handle_send_with_attachments(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body="Test Body",
        attach=["file1.txt", "file2.pdf"]
    )
    mock_manager.sender.send_email.return_value = (True, "Sent")
    
    handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_called_once()
    assert mock_manager.sender.send_email.call_args[1]['attachments'] == ["file1.txt", "file2.pdf"]

@patch('cli.commands.send.console')
def test_handle_send_exception(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body="Test Body",
        attach=None
    )
    mock_manager.sender.send_email.side_effect = Exception("SMTP Error")
    
    handle_send(args, mock_manager)
    
    assert any("error: smtp error" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.send.config.get_encryption_password')
@patch('cli.commands.send.console')
def test_handle_send_password_cancel(mock_console, mock_get_pass, mock_manager):
    args = argparse.Namespace(account="test_acc", to="to@test.com", subject="sub", body="body", attach=None)
    mock_manager.encryption_enabled = True
    mock_get_pass.return_value = None
    
    handle_send(args, mock_manager)
    
    mock_get_pass.assert_called_once()
    mock_manager.sender.send_email.assert_not_called()

@patch('questionary.text')
@patch('cli.commands.send.console')
def test_handle_send_no_body(mock_console, mock_text, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body=None,
        attach=None
    )
    mock_text.return_value.ask.return_value = None
    
    handle_read_result = handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_not_called()
