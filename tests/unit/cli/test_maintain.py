import pytest
import argparse
import os
import shutil
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
    with patch('cli.maintain.get_install_dir') as mock_dir:
        mock_dir.return_value.exists.return_value = True
        version_file = mock_dir.return_value / ".version"
        version_file.read_text.return_value = "v1.0.0"
        
        mock_url.return_value.__enter__.return_value.read.return_value = b"v1.0.0"
        handle_upgrade(args, mock_manager)
        assert any("already up to date" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.console')
@patch('questionary.confirm')
@patch('cli.maintain.tempfile.TemporaryDirectory')
def test_handle_upgrade_new_version(mock_temp, mock_confirm, mock_console, mock_url, mock_manager):
    args = argparse.Namespace(force=False, yes=False)
    mock_confirm.return_value.ask.return_value = True
    
    with patch('cli.maintain.get_install_dir') as mock_dir:
        mock_install_dir = mock_dir.return_value
        mock_install_dir.exists.return_value = True
        (mock_install_dir / ".version").read_text.return_value = "v1.0.0"
        
        # Mock new version and changelog
        mock_resp_version = MagicMock()
        mock_resp_version.__enter__.return_value.read.return_value = b"v1.1.0"
        mock_resp_changelog = MagicMock()
        mock_resp_changelog.__enter__.return_value.read.return_value = b"## [v1.1.0]\n- Test"
        mock_url.side_effect = [mock_resp_version, mock_resp_changelog]
        
        with patch('cli.maintain.shutil.which', return_value="/usr/bin/git"):
            with patch('subprocess.run') as mock_run:
                with patch('os.listdir', return_value=[]):
                    handle_upgrade(args, mock_manager)
                    assert mock_console.print.called
                    assert any("successfully upgraded" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('questionary.confirm')
@patch('cli.maintain.console')
@patch('shutil.rmtree')
def test_handle_uninstall_success(mock_rmtree, mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace(non_interactive=False, keep_data=False)
    mock_confirm.return_value.ask.side_effect = [True, False] # Confirm uninstall, don't keep data
    
    with patch('cli.maintain.get_install_dir') as mock_dir:
        mock_dir.return_value.exists.return_value = True
        handle_uninstall(args, mock_manager)
        assert any("uninstalled" in str(call).lower() for call in mock_console.print.call_args_list)
        assert mock_rmtree.called

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.console')
def test_handle_upgrade_error(mock_console, mock_url, mock_manager):
    args = argparse.Namespace(force=False)
    mock_url.side_effect = Exception("Network Error")
    with patch('cli.maintain.get_install_dir') as mock_dir:
        mock_dir.return_value.exists.return_value = True
        handle_upgrade(args, mock_manager)
        assert any("error" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('questionary.confirm')
@patch('cli.maintain.console')
def test_handle_uninstall_cancel(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace(non_interactive=False)
    mock_confirm.return_value.ask.return_value = False
    handle_uninstall(args, mock_manager)
    assert not mock_console.print.called

@patch('questionary.confirm')
@patch('cli.maintain.console')
def test_handle_uninstall_error(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace(non_interactive=False, keep_data=False)
    mock_confirm.return_value.ask.side_effect = [True, False]
    with patch('shutil.rmtree', side_effect=Exception("Uninstall Failed")):
        with patch('cli.maintain.get_install_dir') as mock_dir:
            mock_dir.return_value.exists.return_value = True
            handle_uninstall(args, mock_manager)
            assert any("uninstall failed" in str(call).lower() for call in mock_console.print.call_args_list)
