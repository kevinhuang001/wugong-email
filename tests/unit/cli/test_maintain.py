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
@patch('cli.maintain.CLIRenderer.render_message')
@patch('cli.maintain.console')
def test_handle_upgrade_already_latest(mock_console, mock_render_message, mock_url, mock_manager):
    args = argparse.Namespace(force=False, json=False)
    with patch('cli.maintain.get_install_dir') as mock_dir:
        mock_dir.return_value.exists.return_value = True
        version_file = mock_dir.return_value / ".version"
        version_file.read_text.return_value = "v1.0.0"
        
        mock_url.return_value.__enter__.return_value.read.return_value = b"v1.0.0"
        handle_upgrade(args, mock_manager)
        mock_render_message.assert_called_once()
        assert "already up to date" in mock_render_message.call_args[0][0].lower()

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.CLIRenderer.render_message')
@patch('cli.maintain.console')
def test_handle_upgrade_already_latest_json(mock_console, mock_render_message, mock_url, mock_manager):
    args = argparse.Namespace(force=False, json=True)
    with patch('cli.maintain.get_install_dir') as mock_dir:
        mock_dir.return_value.exists.return_value = True
        version_file = mock_dir.return_value / ".version"
        version_file.read_text.return_value = "v1.0.0"
        
        mock_url.return_value.__enter__.return_value.read.return_value = b"v1.0.0"
        handle_upgrade(args, mock_manager)
        mock_render_message.assert_called_once()
        assert mock_render_message.call_args[1]['json_output'] is True
        assert "already up to date" in mock_render_message.call_args[0][0].lower()

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.CLIRenderer.render_message')
@patch('cli.maintain.console')
@patch('questionary.confirm')
@patch('cli.maintain.tempfile.TemporaryDirectory')
def test_handle_upgrade_cleanup_obsolete(mock_temp, mock_confirm, mock_console, mock_render_message, mock_url, mock_manager, tmp_path):
    """Test that upgrade removes obsolete files but keeps protected ones."""
    args = argparse.Namespace(force=False, yes=True, json=False)
    
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    (install_dir / ".version").write_text("v1.0.0")
    
    # Create some files in install_dir
    (install_dir / "obsolete.py").write_text("old")
    (install_dir / "config.toml").write_text("config")
    (install_dir / "data.db").write_text("data")
    (install_dir / ".git").mkdir()
    
    # Source (temp) directory
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    (temp_dir / "main.py").write_text("new")
    # Note: obsolete.py is NOT in temp_dir
    
    mock_temp.return_value.__enter__.return_value = temp_dir
    
    with patch('cli.maintain.get_install_dir', return_value=install_dir):
        # Mock responses
        mock_resp_version = MagicMock()
        mock_resp_version.__enter__.return_value.read.return_value = b"v1.1.0"
        mock_url.side_effect = [mock_resp_version, MagicMock()]
        
        with patch('cli.maintain.shutil.which', return_value="/usr/bin/git"):
            with patch('subprocess.run'):
                handle_upgrade(args, mock_manager)
                
                assert not (install_dir / "obsolete.py").exists()
                assert (install_dir / "config.toml").exists()
                assert (install_dir / "data.db").exists()
                assert (install_dir / ".git").exists()
                assert (install_dir / "main.py").exists()

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.CLIRenderer.render_message')
@patch('cli.maintain.console')
@patch('questionary.confirm')
@patch('cli.maintain.tempfile.TemporaryDirectory')
def test_handle_upgrade_new_version(mock_temp, mock_confirm, mock_console, mock_render_message, mock_url, mock_manager, tmp_path):
    args = argparse.Namespace(force=False, yes=False, json=False)
    mock_confirm.return_value.ask.return_value = True
    
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    (install_dir / ".version").write_text("v1.0.0")
    
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    (temp_dir / "main.py").write_text("new")
    
    mock_temp.return_value.__enter__.return_value = temp_dir
    
    with patch('cli.maintain.get_install_dir', return_value=install_dir):
        # Mock new version and changelog
        mock_resp_version = MagicMock()
        mock_resp_version.__enter__.return_value.read.return_value = b"v1.1.0"
        mock_resp_changelog = MagicMock()
        mock_resp_changelog.__enter__.return_value.read.return_value = b"## [v1.1.0]\n- Test"
        mock_url.side_effect = [mock_resp_version, mock_resp_changelog]
        
        with patch('cli.maintain.shutil.which', return_value="/usr/bin/git"):
            with patch('subprocess.run') as mock_run:
                handle_upgrade(args, mock_manager)
                assert (install_dir / "main.py").exists()
                assert any("successfully upgraded" in str(call[0][0]).lower() for call in mock_render_message.call_args_list)

@patch('questionary.confirm')
@patch('cli.maintain.CLIRenderer.render_message')
@patch('cli.maintain.console')
@patch('shutil.rmtree')
def test_handle_uninstall_success(mock_rmtree, mock_console, mock_render_message, mock_confirm, mock_manager):
    args = argparse.Namespace(non_interactive=False, keep_data=False, json=False)
    mock_confirm.return_value.ask.side_effect = [True, False] # Confirm uninstall, don't keep data
    
    with patch('cli.maintain.get_install_dir') as mock_dir:
        mock_dir.return_value.exists.return_value = True
        handle_uninstall(args, mock_manager)
        assert any("uninstalled" in str(call[0][0]).lower() for call in mock_render_message.call_args_list)
        assert mock_rmtree.called

@patch('cli.maintain.urllib.request.urlopen')
@patch('cli.maintain.CLIRenderer.render_message')
@patch('cli.maintain.console')
def test_handle_upgrade_error(mock_console, mock_render_message, mock_url, mock_manager):
    args = argparse.Namespace(force=False, json=False)
    mock_url.side_effect = Exception("Network Error")
    with patch('cli.maintain.get_install_dir') as mock_dir:
        mock_dir.return_value.exists.return_value = True
        handle_upgrade(args, mock_manager)
        assert any("error" in str(call[0][0]).lower() for call in mock_render_message.call_args_list)

@patch('questionary.confirm')
@patch('cli.maintain.CLIRenderer.render_message')
@patch('cli.maintain.console')
def test_handle_uninstall_cancel(mock_console, mock_render_message, mock_confirm, mock_manager):
    args = argparse.Namespace(non_interactive=False, json=False)
    mock_confirm.return_value.ask.return_value = False
    handle_uninstall(args, mock_manager)
    assert not mock_render_message.called

@patch('questionary.confirm')
@patch('cli.maintain.CLIRenderer.render_message')
@patch('cli.maintain.console')
def test_handle_uninstall_error(mock_console, mock_render_message, mock_confirm, mock_manager):
    args = argparse.Namespace(non_interactive=False, keep_data=False, json=False)
    mock_confirm.return_value.ask.side_effect = [True, False]
    with patch('shutil.rmtree', side_effect=Exception("Uninstall Failed")):
        with patch('cli.maintain.get_install_dir') as mock_dir:
            mock_dir.return_value.exists.return_value = True
            handle_uninstall(args, mock_manager)
            assert any("uninstall failed" in str(call[0][0]).lower() for call in mock_render_message.call_args_list)
