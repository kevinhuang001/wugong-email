import pytest
import argparse
from unittest.mock import MagicMock, patch
from cli.commands.account import handle_account, EMAIL_PROVIDERS, account_add_wizard

def get_mock_args(**kwargs):
    defaults = {
        'account_command': 'list',
        'friendly_name': None,
        'provider': None,
        'login_method': None,
        'username': None,
        'imap_server': None,
        'imap_port': None,
        'imap_tls': None,
        'smtp_server': None,
        'smtp_port': None,
        'smtp_tls': None,
        'password': None,
        'client_id': None,
        'client_secret': None,
        'auth_url': None,
        'token_url': None,
        'scopes': None,
        'redirect_uri': None,
        'sync_limit': None,
        'non_interactive': False,
        'password_override': None,
        'name': None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)

def test_email_providers_structure():
    assert "gmail" in EMAIL_PROVIDERS
    assert "outlook" in EMAIL_PROVIDERS
    assert "other" in EMAIL_PROVIDERS
    assert EMAIL_PROVIDERS["gmail"]["imap_server"] == "imap.gmail.com"

@patch('questionary.select')
@patch('questionary.text')
@patch('questionary.password')
def test_account_add_wizard_call(mock_password, mock_text, mock_select):
    # This is more of a placeholder as wizard.py is heavily interactive
    # and would require complex mocking of the entire flow.
    # We'll just verify the wizard can be called with everything mocked.
    mock_select.return_value.ask.return_value = "other"
    mock_text.return_value.ask.return_value = "test"
    mock_password.return_value.ask.return_value = "pwd"
    
    with patch('cli.commands.account.test_imap_connection', return_value=(True, "")):
        res = account_add_wizard(friendly_name="test", non_interactive=False)
        assert isinstance(res, tuple)
        assert len(res) == 2

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    manager.syncer = MagicMock()
    return manager

@patch('cli.commands.account.console')
def test_handle_account_list(mock_console, mock_manager):
    args = get_mock_args(account_command="list")
    mock_parser = MagicMock()
    
    handle_account(args, mock_manager, mock_parser)
    
    assert mock_console.print.called

@patch('cli.commands.account.questionary.confirm')
@patch('cli.commands.account.console')
def test_handle_account_delete_success(mock_console, mock_confirm, mock_manager):
    args = get_mock_args(
        account_command="delete",
        name="test_acc"
    )
    # Mock questionary confirmation
    mock_confirm.return_value.ask.return_value = True
    
    # Ensure manager.accounts has the account
    mock_manager.accounts = [{"friendly_name": "test_acc"}]
    mock_manager.get_account_by_name.return_value = mock_manager.accounts[0]
    
    mock_parser = MagicMock()
    
    handle_account(args, mock_manager, mock_parser)
    
    assert mock_console.print.called
    # Check if accounts was updated
    assert mock_manager.accounts == []

from unittest.mock import MagicMock, patch, ANY

@patch('cli.commands.account.config.get_encryption_password')
@patch('cli.commands.account.MailManager')
@patch('cli.commands.account.Progress')
@patch('cli.commands.account.console')
@patch('cli.commands.account.account_add_wizard')
def test_handle_account_add_password_cancel(mock_wizard, mock_console, mock_progress, mock_mail_manager, mock_get_pass, mock_manager):
    args = get_mock_args(account_command="add")
    new_acc = {"friendly_name": "new_acc"}
    mock_wizard.return_value = ([(new_acc, 10)], None)
    mock_parser = MagicMock()
    
    # Mock MailManager instance
    mock_mm_instance = MagicMock()
    mock_mail_manager.return_value = mock_mm_instance
    mock_mm_instance.encryption_enabled = True
    mock_mm_instance.config = {"general": {"encrypt_emails": True}}
    
    # Mock password cancel
    mock_get_pass.return_value = None
    
    handle_account(args, mock_manager, mock_parser)
    
    mock_get_pass.assert_called()
    mock_mm_instance.syncer.sync_emails.assert_not_called()

@patch('cli.commands.account.config.get_encryption_password')
@patch('cli.commands.account.MailManager')
@patch('cli.commands.account.Progress')
@patch('cli.commands.account.console')
@patch('cli.commands.account.account_add_wizard')
def test_handle_account_add_with_password_prompt(mock_wizard, mock_console, mock_progress, mock_mail_manager, mock_get_pass, mock_manager):
    args = get_mock_args(account_command="add")
    new_acc = {"friendly_name": "new_acc"}
    mock_wizard.return_value = ([(new_acc, 10)], "some_password")
    mock_parser = MagicMock()
    
    # Mock MailManager instance
    mock_mm_instance = MagicMock()
    mock_mail_manager.return_value = mock_mm_instance
    mock_mm_instance.encryption_enabled = True
    mock_mm_instance.config = {"general": {"encrypt_emails": True}}
    
    # Mock Progress context manager
    mock_progress_instance = mock_progress.return_value.__enter__.return_value
    
    handle_account(args, mock_manager, mock_parser)
    
    mock_mm_instance.syncer.sync_emails.assert_called_once_with(
        new_acc, "some_password", limit=10, is_initial_sync=True, progress_callback=ANY
    )

@patch('cli.commands.account.MailManager')
@patch('cli.commands.account.Progress')
@patch('cli.commands.account.console')
@patch('cli.commands.account.account_add_wizard')
def test_handle_account_add_progress_callback(mock_wizard, mock_console, mock_progress, mock_mail_manager, mock_manager):
    args = get_mock_args(account_command="add", password="test_password")
    new_acc = {"friendly_name": "new_acc"}
    mock_wizard.return_value = ([(new_acc, 10)], "test_password")
    mock_parser = MagicMock()
    
    # Mock MailManager instance
    mock_mm_instance = MagicMock()
    mock_mail_manager.return_value = mock_mm_instance
    
    # Mock Progress context manager
    mock_progress_instance = mock_progress.return_value.__enter__.return_value
    
    # Capture the progress callback
    def side_effect(*args, **kwargs):
        callback = kwargs.get('progress_callback')
        if callback:
            callback(5, 10, "testing progress")
        return None
        
    mock_mm_instance.syncer.sync_emails.side_effect = side_effect
    
    handle_account(args, mock_manager, mock_parser)
    
    # Verify progress.update was called
    mock_progress_instance.update.assert_called()
    update_args = mock_progress_instance.update.call_args[1]
    assert update_args['completed'] == 5
    assert update_args['total'] == 10
    assert "testing progress" in update_args['description']

@patch('cli.commands.account.config.get_encryption_password')
@patch('cli.commands.account.MailManager')
@patch('cli.commands.account.Progress')
@patch('cli.commands.account.console')
@patch('cli.commands.account.account_add_wizard')
def test_handle_account_add_with_sync(mock_wizard, mock_console, mock_progress, mock_mail_manager, mock_get_pass, mock_manager):
    args = get_mock_args(account_command="add", password="test_password")
    # Mock return value of wizard: (newly_added, password)
    new_acc = {"friendly_name": "new_acc"}
    mock_wizard.return_value = ([(new_acc, 10)], "test_password")
    mock_parser = MagicMock()
    
    # Mock MailManager instance
    mock_mm_instance = MagicMock()
    mock_mail_manager.return_value = mock_mm_instance
    mock_mm_instance.encryption_enabled = False
    mock_mm_instance.config = {"general": {"encrypt_emails": False}}
    
    # Mock Progress context manager
    mock_progress_instance = mock_progress.return_value.__enter__.return_value
    
    handle_account(args, mock_manager, mock_parser)
    
    mock_wizard.assert_called_once()
    mock_mm_instance.syncer.sync_emails.assert_called_once()
    assert any("initial sync complete" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.account.MailManager')
@patch('cli.commands.account.console')
@patch('cli.commands.account.account_add_wizard')
def test_handle_account_add_skip_sync(mock_wizard, mock_console, mock_mail_manager, mock_manager):
    args = get_mock_args(account_command="add")
    new_acc = {"friendly_name": "new_acc"}
    mock_wizard.return_value = ([(new_acc, 0)], "test_password")
    mock_parser = MagicMock()
    
    # Mock MailManager instance
    mock_mm_instance = MagicMock()
    mock_mail_manager.return_value = mock_mm_instance
    mock_mm_instance.encryption_enabled = False
    mock_mm_instance.config = {"general": {"encrypt_emails": False}}
    
    handle_account(args, mock_manager, mock_parser)
    
    assert any("skipping initial sync" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.account.MailManager')
@patch('cli.commands.account.console')
@patch('cli.commands.account.account_add_wizard')
def test_handle_account_add_sync_error(mock_wizard, mock_console, mock_mail_manager, mock_manager):
    args = get_mock_args(account_command="add")
    new_acc = {"friendly_name": "new_acc"}
    mock_wizard.return_value = ([(new_acc, 10)], "test_password")
    mock_parser = MagicMock()
    
    # Mock MailManager instance
    mock_mm_instance = MagicMock()
    mock_mail_manager.return_value = mock_mm_instance
    mock_mm_instance.encryption_enabled = False
    mock_mm_instance.config = {"general": {"encrypt_emails": False}}
    mock_mm_instance.syncer.sync_emails.side_effect = Exception("Sync Error")
    
    # Mock Progress context manager
    with patch('cli.commands.account.Progress'):
        handle_account(args, mock_manager, mock_parser)
    
    assert any("error syncing" in str(call).lower() for call in mock_console.print.call_args_list)

def test_handle_account_unknown_command(mock_manager):
    args = get_mock_args(account_command="unknown")
    mock_parser = MagicMock()
    handle_account(args, mock_manager, mock_parser)
    mock_parser.print_help.assert_called_once()

@patch('cli.commands.account.console')
def test_handle_account_list_empty(mock_console, mock_manager):
    args = get_mock_args(account_command="list")
    mock_manager.accounts = []
    mock_parser = MagicMock()
    
    handle_account(args, mock_manager, mock_parser)
    
    assert mock_console.print.called
    # Should say something about no accounts
    any_call_contains_no_accounts = any("no accounts" in str(call).lower() or "configured accounts" in str(call).lower() for call in mock_console.print.call_args_list)
    assert any_call_contains_no_accounts

@patch('cli.commands.account.console')
def test_handle_account_delete_not_found(mock_console, mock_manager):
    args = get_mock_args(
        account_command="delete",
        name="non_existent"
    )
    mock_manager.get_account_by_name.return_value = None
    mock_parser = MagicMock()
    
    handle_account(args, mock_manager, mock_parser)
    
    assert any("not found" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.account.questionary.confirm')
@patch('cli.commands.account.console')
def test_handle_account_delete_cancel(mock_console, mock_confirm, mock_manager):
    args = get_mock_args(
        account_command="delete",
        name="test_acc"
    )
    mock_confirm.return_value.ask.return_value = False
    mock_manager.accounts = [{"friendly_name": "test_acc"}]
    mock_manager.get_account_by_name.return_value = mock_manager.accounts[0]
    mock_parser = MagicMock()
    
    handle_account(args, mock_manager, mock_parser)
    
    assert any("cancelled" in str(call).lower() for call in mock_console.print.call_args_list)
    assert len(mock_manager.accounts) == 1

@patch('cli.commands.account.console')
@patch('cli.commands.account.account_add_wizard')
def test_handle_account_add_no_change(mock_wizard, mock_console, mock_manager):
    args = get_mock_args(account_command="add")
    mock_wizard.return_value = (None, None)
    mock_parser = MagicMock()
    
    handle_account(args, mock_manager, mock_parser)
    
    mock_wizard.assert_called_once()
