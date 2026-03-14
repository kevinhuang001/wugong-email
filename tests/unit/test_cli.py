import pytest
from unittest.mock import MagicMock, patch
from cli import handle_list, handle_delete, handle_sync
import argparse

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.console')
def test_handle_list_success(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        keyword=None,
        from_user=None,
        since=None,
        before=None,
        all=False,
        limit=10,
        local=False,
        password="test_password"
    )
    
    # Mock reader.query_emails
    mock_manager.reader.query_emails.return_value = (
        [{"id": "1", "from": "sender", "subject": "test", "date": "2024-01-01", "seen": True}],
        {"is_offline": False}
    )
    
    handle_list(args, mock_manager)
    
    # Verify reader.query_emails was called
    mock_manager.reader.query_emails.assert_called_once()
    # Verify table was printed (mock_console.print is called)
    assert mock_console.print.called

@patch('questionary.confirm')
@patch('cli.console')
def test_handle_delete_success(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        id="123"
    )
    mock_confirm.return_value.ask.return_value = True
    mock_manager.reader.delete_email.return_value = (True, "Deleted")
    
    handle_delete(args, mock_manager)
    
    # Verify reader.delete_email was called
    mock_manager.reader.delete_email.assert_called_once_with(mock_manager.accounts[0], "", "123")
    assert mock_console.print.called

@patch('cli.console')
def test_handle_sync_success(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        limit=20,
        all=False,
        password="test_password"
    )
    mock_manager.reader.fetch_emails.return_value = ([], {})
    
    handle_sync(args, mock_manager)
    
    # Verify reader.fetch_emails was called
    mock_manager.reader.fetch_emails.assert_called_once()
    assert mock_console.print.called

@patch('cli.console')
def test_handle_read_success(mock_console, mock_manager):
    from cli import handle_read
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        html=False
    )
    
    # Mock reader.read_email
    mock_manager.reader.read_email.return_value = "Email Content"
    
    handle_read(args, mock_manager)
    
    # Verify reader.read_email was called
    mock_manager.reader.read_email.assert_called_once_with(mock_manager.accounts[0], "", "123")
    assert mock_console.print.called

@patch('cli.console')
def test_handle_list_no_accounts(mock_console, mock_manager):
    mock_manager.accounts = []
    args = argparse.Namespace(account="test_acc")
    
    handle_list(args, mock_manager)
    
    mock_console.print.assert_called_with("[yellow]No accounts configured yet. Run 'wugong account add' to get started.[/yellow]")

@patch('questionary.text')
@patch('cli.console')
def test_handle_send_success(mock_console, mock_text, mock_manager):
    from cli import handle_send
    args = argparse.Namespace(
        account="test_acc",
        to="recipient@test.com",
        subject="Test Subject",
        body="Test Body",
        attach=None
    )
    
    handle_send(args, mock_manager)
    
    mock_manager.sender.send_email.assert_called_once_with(
        mock_manager.accounts[0],
        "",
        to="recipient@test.com",
        subject="Test Subject",
        body="Test Body",
        attachments=None
    )
    assert mock_console.print.called

@patch('cli.console')
def test_handle_account_list(mock_console, mock_manager):
    from cli import handle_account
    args = argparse.Namespace(account_command="list")
    
    handle_account(args, mock_manager, MagicMock())
    
    assert mock_console.print.called

@patch('questionary.confirm')
@patch('cli.console')
def test_handle_account_delete_success(mock_console, mock_confirm, mock_manager):
    from cli import handle_account
    args = argparse.Namespace(account_command="delete", name="test_acc")
    mock_confirm.return_value.ask.return_value = True
    
    handle_account(args, mock_manager, MagicMock())
    
    # Verify account was removed and config saved
    assert len(mock_manager.accounts) == 0
    mock_manager._save_config.assert_called_once()
    assert mock_console.print.called

@patch('cli.console')
@patch('questionary.select')
def test_handle_read_html_only(mock_select, mock_console, mock_manager):
    from cli import handle_read
    args = argparse.Namespace(
        account="test_acc",
        id="123",
        text=False,
        html=False
    )
    
    # Mock reader.read_email to return html_only content
    mock_manager.reader.read_email.return_value = {"type": "html_only", "html": "<html><body>Hello</body></html>"}
    mock_select.return_value.ask.return_value = "Extract text (may be incomplete, sentences might run together)"
    
    # Mock sys.stdin.isatty to True to test interactive choice
    with patch('sys.stdin.isatty', return_value=True):
        handle_read(args, mock_manager)
    
    assert mock_select.called
    assert mock_console.print.called

@patch('cli.console')
def test_version_arg(mock_console):
    from cli import main
    # Create a wrapper for open that only mocks .version
    original_open = open
    def side_effect(path, *args, **kwargs):
        if str(path).endswith(".version"):
            from unittest.mock import mock_open
            return mock_open(read_data="1.0.0")()
        return original_open(path, *args, **kwargs)

    with patch('sys.argv', ['cli.py', '--version']):
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect):
                main()
    mock_console.print.assert_called_with("Wugong Email v1.0.0")

@patch('cli.account_add_wizard')
@patch('cli.console')
def test_handle_account_add(mock_console, mock_wizard, mock_manager):
    from cli import handle_account
    args = argparse.Namespace(account_command="add")
    mock_wizard.return_value = ([], "test_password") # No accounts added
    
    handle_account(args, mock_manager, MagicMock())
    
    assert mock_wizard.called

@patch('cli.init_wizard')
def test_handle_init(mock_wizard, mock_manager):
    from cli import handle_init
    handle_init(None, mock_manager)
    assert mock_wizard.called

@patch('cli.configure_wizard')
def test_handle_configure(mock_wizard, mock_manager):
    from cli import handle_configure
    handle_configure(None, mock_manager)
    assert mock_wizard.called

@patch('urllib.request.urlopen')
@patch('cli.console')
def test_handle_upgrade_already_latest(mock_console, mock_urlopen):
    from cli import handle_upgrade
    # Mock current version
    original_open = open
    def side_effect(path, *args, **kwargs):
        if str(path).endswith(".version"):
            from unittest.mock import mock_open
            return mock_open(read_data="1.0.0")()
        return original_open(path, *args, **kwargs)

    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', side_effect):
            # Mock online version
            mock_response = MagicMock()
            mock_response.read.return_value = b"1.0.0"
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            handle_upgrade()
            
    mock_console.print.assert_any_call("[green]✅ Wugong Email is already up to date (v1.0.0).[/green]")

@patch('subprocess.run')
def test_handle_uninstall(mock_run):
    from cli import handle_uninstall
    with patch('os.name', 'posix'):
        handle_uninstall()
        assert mock_run.called
        # Check if bash was called with uninstall.sh
        args, kwargs = mock_run.call_args
        assert "uninstall.sh" in args[0][1]
