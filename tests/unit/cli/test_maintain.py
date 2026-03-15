import pytest
import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch
from cli.maintain import handle_upgrade, handle_uninstall

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.console')
def test_handle_upgrade_already_latest(mock_console, mock_url, mock_manager):
    args = argparse.Namespace(force=False)
    with patch('cli.maintain.Path.exists', return_value=True):
        with patch('cli.maintain.Path.read_text', return_value="v1.0.0"):
            mock_url.return_value.__enter__.return_value.read.return_value = b"v1.0.0"
            handle_upgrade(args, mock_manager)
            assert mock_console.print.called

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.console')
@patch('builtins.open', new_callable=MagicMock)
def test_handle_upgrade_new_version(mock_open, mock_console, mock_url, mock_manager):
    args = argparse.Namespace(force=False)
    with patch('cli.maintain.Path.exists', return_value=True):
        with patch('cli.maintain.Path.read_text', return_value="v1.0.0"):
            # Mock new version available
            mock_resp_version = MagicMock()
            mock_resp_version.__enter__.return_value.read.return_value = b"v1.1.0"
            
            mock_resp_script = MagicMock()
            mock_resp_script.__enter__.return_value.read.return_value = b"echo 'updating'"
            
            mock_url.side_effect = [mock_resp_version, mock_resp_script]
            
            with patch('subprocess.run') as mock_run:
                with patch('os.chmod'):
                    handle_upgrade(args, mock_manager)
                    assert mock_console.print.called
                    assert any("successfully upgraded" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.console')
@patch('builtins.open', new_callable=MagicMock)
def test_handle_upgrade_new_version_windows(mock_open, mock_console, mock_url, mock_manager):
    args = argparse.Namespace(force=False)
    # Mock Path to avoid WindowsPath instantiation error on macOS
    with patch('cli.maintain.Path') as mock_path_cls:
        mock_install_dir = MagicMock()
        mock_path_cls.home.return_value = mock_install_dir
        mock_install_dir.__truediv__.return_value = mock_install_dir
        mock_install_dir.exists.return_value = True
        mock_install_dir.read_text.return_value = "v1.0.0"
        
        # Mock new version available
        mock_resp_version = MagicMock()
        mock_resp_version.__enter__.return_value.read.return_value = b"v1.1.0"
        
        mock_resp_script = MagicMock()
        mock_resp_script.__enter__.return_value.read.return_value = b"echo 'updating'"
        
        mock_url.side_effect = [mock_resp_version, mock_resp_script]
        
        with patch('subprocess.run') as mock_run:
            with patch('os.name', 'nt'):
                handle_upgrade(args, mock_manager)
                assert mock_console.print.called
                # Verify powershell was called
                mock_run.assert_called_once()
                assert mock_run.call_args[0][0][0] == "powershell"

@patch('questionary.confirm')
@patch('cli.maintain.console')
def test_handle_uninstall_script_not_found(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace()
    mock_confirm.return_value.ask.return_value = True
    with patch('cli.maintain.Path.exists', return_value=False):
        handle_uninstall(args, mock_manager)
        assert any("uninstall script not found" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('questionary.confirm')
@patch('cli.maintain.console')
def test_handle_uninstall_success(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace()
    mock_confirm.return_value.ask.return_value = True
    with patch('subprocess.run') as mock_run:
        with patch('cli.maintain.Path.exists', return_value=True):
            handle_uninstall(args, mock_manager)
            assert any("uninstalled" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.console')
def test_handle_upgrade_error(mock_console, mock_url, mock_manager):
    args = argparse.Namespace(force=False)
    mock_url.side_effect = Exception("Network Error")
    handle_upgrade(args, mock_manager)
    assert any("error" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('questionary.confirm')
@patch('cli.maintain.console')
def test_handle_uninstall_cancel(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace()
    mock_confirm.return_value.ask.return_value = False
    handle_uninstall(args, mock_manager)
    assert not mock_console.print.called

@patch('questionary.confirm')
@patch('cli.maintain.console')
def test_handle_uninstall_error(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace()
    mock_confirm.return_value.ask.return_value = True
    with patch('subprocess.run', side_effect=Exception("Uninstall Failed")):
        with patch('cli.maintain.Path.exists', return_value=True):
            handle_uninstall(args, mock_manager)
            assert any("uninstall failed" in str(call).lower() for call in mock_console.print.call_args_list)
