import pytest
import argparse
from unittest.mock import MagicMock, patch, ANY
from cli.commands.send import handle_send

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.render.CLIRenderer.render_message')
def test_handle_send_success(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body="Test Body",
        attach=None,
        json=False
    )
    # Correct mock for sender.send_email
    mock_manager.sender.send_email.return_value = (True, "Sent")
    
    handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_called_once()
    mock_render.assert_called_once_with(ANY, type="success", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_send_success_json(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body="Test Body",
        attach=None,
        json=True
    )
    # Correct mock for sender.send_email
    mock_manager.sender.send_email.return_value = (True, "Sent")
    
    handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_called_once()
    mock_render.assert_called_once_with(ANY, type="success", json_output=True)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_send_account_not_found(mock_render, mock_manager):
    args = argparse.Namespace(account="non_existent", to="to@test.com", subject="sub", body="body", attach=None, json=False)
    mock_manager.get_account_by_name.return_value = None
    
    handle_send(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('questionary.text')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_send_interactive_body(mock_render, mock_text, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body=None,
        attach=None,
        json=False
    )
    mock_text.return_value.ask.return_value = "Interactive Body"
    mock_manager.sender.send_email.return_value = (True, "Sent")
    
    handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_called_once()
    assert "Interactive Body" in mock_manager.sender.send_email.call_args[1]['body']

@patch('cli.render.CLIRenderer.render_message')
def test_handle_send_with_attachments(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body="Test Body",
        attach=["file1.txt", "file2.pdf"],
        json=False
    )
    mock_manager.sender.send_email.return_value = (True, "Sent")
    
    handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_called_once()
    assert mock_manager.sender.send_email.call_args[1]['attachments'] == ["file1.txt", "file2.pdf"]

@patch('cli.render.CLIRenderer.render_message')
def test_handle_send_exception(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body="Test Body",
        attach=None,
        json=False
    )
    mock_manager.sender.send_email.side_effect = Exception("SMTP Error")
    
    handle_send(args, mock_manager)
    
    mock_render.assert_called_with(ANY, type="error", json_output=False)

@patch('cli.commands.send.config.get_verified_password')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_send_password_cancel(mock_render, mock_get_pass, mock_manager):
    args = argparse.Namespace(account="test_acc", to="to@test.com", subject="sub", body="body", attach=None, json=False)
    mock_manager.encryption_enabled = True
    mock_get_pass.side_effect = ValueError("cancelled")
    
    handle_send(args, mock_manager)
    
    mock_get_pass.assert_called_once()
    mock_manager.sender.send_email.assert_not_called()
    mock_render.assert_called_with(ANY, type="error", json_output=False)

@patch('questionary.text')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_send_no_body(mock_render, mock_text, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body=None,
        attach=None,
        json=False
    )
    mock_text.return_value.ask.return_value = None
    
    handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_not_called()
    mock_render.assert_called_with(ANY, type="error", json_output=False)
