import pytest
import argparse
from unittest.mock import MagicMock, patch
from cli.configure import handle_init, handle_configure, init_wizard

@patch('cli.configure.generate_salt')
@patch('questionary.confirm')
@patch('questionary.select')
@patch('questionary.text')
@patch('cli.configure.config.save_config')
def test_init_wizard_minimal(mock_save, mock_text, mock_select, mock_confirm, mock_salt):
    mock_confirm.return_value.ask.return_value = True
    mock_select.return_value.ask.return_value = "INFO"
    mock_text.return_value.ask.return_value = "test"
    mock_salt.return_value = b"salt"
    
    # Mocking config and other interactive parts is complex, 
    # so we'll just check if it can run with everything mocked.
    with patch('cli.configure.config.load_config') as mock_load, \
         patch('questionary.password') as mock_pwd:
        mock_load.return_value = {"general": {}} # Empty config to trigger initialization
        mock_pwd.return_value.ask.return_value = "pwd"
        with patch('cli.commands.account.account_add_wizard') as mock_add:
            mock_add.return_value = ([], "pwd")
            init_wizard()
            assert mock_save.called

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

def get_mock_args(**kwargs):
    defaults = {
        'encrypt_creds': None,
        'encrypt_emails': None,
        'password': None,
        'console_log_level': None,
        'file_log_level': None,
        'sync_interval': None,
        'non_interactive': False,
        'json': False
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)

@patch('cli.configure.CLIRenderer.render_message')
@patch('cli.configure.console')
@patch('cli.configure.init_wizard')
def test_handle_init_windows_no_admin(mock_init_wizard, mock_console, mock_render_message, mock_manager):
    args = get_mock_args()
    with patch('os.name', 'nt'):
        # Mock ctypes
        mock_ctypes = MagicMock()
        mock_ctypes.windll.shell32.IsUserAnAdmin.return_value = False
        with patch.dict('sys.modules', {'ctypes': mock_ctypes}):
            handle_init(args, mock_manager)
            assert mock_console.print.called
            assert any("not running as administrator" in str(call).lower() for call in mock_console.print.call_args_list)
    mock_init_wizard.assert_called_once()

@patch('cli.configure.CLIRenderer.render_message')
@patch('cli.configure.console')
@patch('cli.configure.init_wizard')
def test_handle_init_unix(mock_init_wizard, mock_console, mock_render_message, mock_manager):
    args = get_mock_args()
    with patch('os.name', 'posix'):
        handle_init(args, mock_manager)
    mock_init_wizard.assert_called_once()
    # Should not print admin warning on posix
    assert not any("administrator" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.configure.CLIRenderer.render_message')
@patch('cli.configure.console')
@patch('cli.configure.configure_wizard')
def test_handle_configure(mock_configure_wizard, mock_console, mock_render_message, mock_manager):
    args = get_mock_args()
    handle_configure(args, mock_manager)
    mock_configure_wizard.assert_called_once()

@patch('cli.configure.CLIRenderer.render_message')
@patch('cli.configure.init_wizard')
def test_handle_init_json(mock_init_wizard, mock_render_message, mock_manager):
    args = get_mock_args(json=True)
    handle_init(args, mock_manager)
    mock_init_wizard.assert_called_once()
    assert mock_init_wizard.call_args[1]['json_output'] is True

@patch('cli.configure.CLIRenderer.render_message')
@patch('cli.configure.configure_wizard')
def test_handle_configure_json(mock_configure_wizard, mock_render_message, mock_manager):
    args = get_mock_args(json=True)
    handle_configure(args, mock_manager)
    mock_configure_wizard.assert_called_once()
    assert mock_configure_wizard.call_args[1]['json_output'] is True
