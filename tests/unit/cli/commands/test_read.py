import pytest
import argparse
from unittest.mock import MagicMock, patch, ANY
from cli.commands.read import handle_read
from mail.storage_manager import Email

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.render.CLIRenderer.render_email_content')
def test_handle_read_success(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=True,
        raw=False,
        browser=False,
        folder="INBOX",
        json=False
    )
    
    # Mock reader.read_email
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='text/plain', content='body', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    
    handle_read(args, mock_manager)
    
    # Verify reader.read_email was called
    mock_manager.reader.read_email.assert_called_once_with(mock_manager.accounts[0], "", "123", folder="INBOX")
    mock_render.assert_called_once_with(ANY, ANY, json_output=False)

@patch('cli.render.CLIRenderer.render_email_content')
def test_handle_read_html_only(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=True,
        raw=False,
        browser=False,
        folder="INBOX",
        json=False
    )
    
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='html_only', content='<html><body>Test</body></html>', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    
    handle_read(args, mock_manager)
    
    mock_manager.reader.read_email.assert_called_once()
    mock_render.assert_called_once_with(ANY, ANY, json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_read_account_not_found(mock_render, mock_manager):
    args = argparse.Namespace(account="non_existent", id="123", text=False, raw=False, browser=False, json=False)
    mock_manager.get_account_by_name.return_value = None
    
    handle_read(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_read_not_found(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="non_existent",
        text=False,
        raw=False,
        browser=False,
        folder="INBOX",
        json=False
    )
    mock_manager.reader.read_email.return_value = None
    
    handle_read(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="warning", json_output=False)

@patch('webbrowser.open')
@patch('cli.commands.read.console')
def test_handle_read_browser(mock_console, mock_browser, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        raw=False,
        browser=True,
        folder="INBOX"
    )
    
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='text/html', content='<html><body>Test</body></html>', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    mock_browser.return_value = True
    
    handle_read(args, mock_manager)
    
    assert mock_browser.called
    assert any("opened in browser" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('questionary.select')
@patch('webbrowser.open')
@patch('cli.commands.read.console')
def test_handle_read_menu_browser_plain_text(mock_console, mock_browser, mock_select, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        raw=False,
        browser=False,
        folder="INBOX"
    )
    
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='text/plain', content='This is plain text\nwith multiple lines.', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    mock_select.return_value.ask.return_value = "browser"
    mock_browser.return_value = True
    
    with patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True):
        handle_read(args, mock_manager)
    
    assert mock_browser.called
    # The actual file content check would be harder without mocking tempfile,
    # but we can at least verify it didn't crash and called browser.open
    assert any("opened in browser" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('webbrowser.open')
@patch('cli.commands.read.console')
def test_handle_read_browser_fail(mock_console, mock_browser, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        raw=False,
        browser=True,
        folder="INBOX"
    )
    
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='text/html', content='<html><body>Test</body></html>', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    mock_browser.return_value = False # Browser open fails
    
    handle_read(args, mock_manager)
    
    assert mock_browser.called
    assert any("warning: could not open browser" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_read_error_string(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        raw=False,
        browser=False,
        folder="INBOX",
        json=False
    )
    mock_manager.reader.read_email.return_value = "Custom error message"
    
    handle_read(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_read_exception(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        raw=False,
        browser=False,
        folder="INBOX",
        json=False
    )
    mock_manager.reader.read_email.side_effect = Exception("Boom")
    
    handle_read(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('questionary.select')
@patch('cli.commands.read.console')
@patch('cli.render.CLIRenderer.render_email_content')
def test_handle_read_html_only_extract_text(mock_render, mock_console, mock_select, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        raw=False,
        browser=False,
        folder="INBOX"
    )
    
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='html_only', content='<html><body>Test Content</body></html>', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    mock_select.return_value.ask.return_value = "text"
    
    with patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True):
        handle_read(args, mock_manager)
    
    assert "Extracted from HTML" in mock_email.content
    assert "Test Content" in mock_email.content
    assert mock_render.called

@patch('questionary.select')
@patch('cli.commands.read.console')
@patch('cli.render.CLIRenderer.render_email_content')
def test_handle_read_html_only_cancel(mock_render, mock_console, mock_select, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        raw=False,
        browser=False,
        folder="INBOX"
    )
    
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='html_only', content='<html><body>Test Content</body></html>', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    mock_select.return_value.ask.return_value = "cancel"
    
    with patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True):
        handle_read(args, mock_manager)
    
    assert not mock_render.called

@patch('cli.commands.read.config.get_verified_password')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_read_password_cancel(mock_render, mock_get_pass, mock_manager):
    args = argparse.Namespace(account="test_acc", id="123", text=False, raw=False, browser=False, json=False)
    mock_manager.encryption_enabled = True
    mock_get_pass.side_effect = ValueError("cancelled")
    
    handle_read(args, mock_manager)
    
    mock_get_pass.assert_called_once()
    mock_manager.reader.read_email.assert_not_called()
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_email_content')
def test_handle_read_success_json(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=True,
        raw=False,
        browser=False,
        folder="INBOX",
        json=True
    )
    
    # Mock reader.read_email
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='text/plain', content='body', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    
    handle_read(args, mock_manager)
    
    # Verify reader.read_email was called
    mock_manager.reader.read_email.assert_called_once_with(mock_manager.accounts[0], "", "123", folder="INBOX")
    mock_render.assert_called_once_with(ANY, ANY, json_output=True)

@patch('questionary.select')
@patch('cli.commands.read.console')
@patch('cli.render.CLIRenderer.render_email_content')
def test_handle_read_html_only_raw_html(mock_render, mock_console, mock_select, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        raw=False,
        browser=False,
        folder="INBOX"
    )
    
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='html_only', content='<html><body>Test Content</body></html>', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    mock_select.return_value.ask.return_value = "raw"
    
    with patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True):
        handle_read(args, mock_manager)
    
    assert mock_email.content == '<html><body>Test Content</body></html>'
    assert mock_render.called

@patch('questionary.select')
@patch('webbrowser.open')
@patch('cli.commands.read.console')
def test_handle_read_menu_browser(mock_console, mock_browser, mock_select, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        raw=False,
        browser=False,
        folder="INBOX"
    )
    
    mock_email = Email(
        account_name='test_acc', folder='INBOX', uid='123',
        sender='sender', sender_email='sender@test.com',
        subject='test', date='2024-01-01', seen=True,
        content_type='text/html', content='<html><body>Test</body></html>', attachments=[]
    )
    mock_manager.reader.read_email.return_value = mock_email
    mock_select.return_value.ask.return_value = "browser"
    mock_browser.return_value = True
    
    with patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True):
        handle_read(args, mock_manager)
    
    assert mock_browser.called
    assert any("opened in browser" in str(call).lower() for call in mock_console.print.call_args_list)
