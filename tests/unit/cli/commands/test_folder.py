import pytest
import argparse
from unittest.mock import MagicMock, patch, ANY
from cli.commands.folder import handle_folder

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.non_interactive = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.render.CLIRenderer.render_folders_table')
def test_handle_folder_list_success(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="list",
        verbose=False,
        json=False
    )
    mock_manager.folder_manager.list_folders.return_value = ["INBOX", "Sent"]
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_manager.folder_manager.list_folders.assert_called_once()
    mock_render.assert_called_once_with(ANY, "test_acc", verbose=False, json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_create_success(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="create",
        name="NewFolder",
        json=False
    )
    mock_manager.folder_manager.create_folder.return_value = True
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_manager.folder_manager.create_folder.assert_called_once()
    mock_render.assert_called_once_with(ANY, type="success", json_output=False)

@patch('questionary.confirm')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_delete_success(mock_render, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="delete",
        name="OldFolder",
        json=False
    )
    mock_confirm.return_value.ask.return_value = True
    mock_manager.folder_manager.delete_folder.return_value = True
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_manager.folder_manager.delete_folder.assert_called_once()
    mock_render.assert_called_once_with(ANY, type="success", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_move_success(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="move",
        id="1,2,3",
        src="INBOX",
        dest="Archive",
        json=False
    )
    mock_manager.folder_manager.move_emails.return_value = True
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_manager.folder_manager.move_emails.assert_called_once_with(
        mock_manager.connector.get_imap_connection.return_value,
        ["1", "2", "3"], "INBOX", "Archive"
    )
    mock_render.assert_called_once_with(ANY, type="success", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_account_not_found(mock_render, mock_manager):
    args = argparse.Namespace(
        account="non_existent",
        folder_command="list",
        json=False
    )
    mock_manager.get_account_by_name.return_value = None
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.commands.folder.config.get_verified_password')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_password_cancel(mock_render, mock_get_pass, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="list", json=False)
    mock_manager.encryption_enabled = True
    mock_get_pass.side_effect = ValueError("cancelled")
    
    handle_folder(args, mock_manager)
    
    mock_get_pass.assert_called_once()
    mock_manager.connector.get_imap_connection.assert_not_called()
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_create_no_name(mock_render, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="create", name=None, json=False)
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_delete_no_name(mock_render, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="delete", name=None, json=False)
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('questionary.confirm')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_delete_failed(mock_render, mock_confirm, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="delete", name="OldFolder", json=False)
    mock_confirm.return_value.ask.return_value = True
    mock_manager.folder_manager.delete_folder.return_value = False
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_move_no_id_or_dest(mock_render, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="move", id=None, dest=None, json=False)
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_logout_exception(mock_render, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="list", json=False)
    mock_mail = MagicMock()
    mock_mail.logout.side_effect = Exception("Logout Error")
    mock_manager.connector.get_imap_connection.return_value = mock_mail
    mock_manager.folder_manager.list_folders.return_value = []
    
    handle_folder(args, mock_manager)
    
    # Should not raise exception
    mock_mail.logout.assert_called_once()

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_general_exception(mock_render, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="list", json=False)
    mock_manager.connector.get_imap_connection.side_effect = Exception("General Error")
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_unknown_command(mock_render, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="unknown", json=False)
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="warning", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_create_failed(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="create",
        name="NewFolder",
        json=False
    )
    mock_manager.folder_manager.create_folder.return_value = False
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('questionary.confirm')
@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_delete_cancel(mock_render, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="delete",
        name="OldFolder",
        json=False
    )
    mock_confirm.return_value.ask.return_value = False
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert mock_manager.folder_manager.delete_folder.call_count == 0

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_move_failed(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="move",
        id="1",
        src="INBOX",
        dest="Archive",
        json=False
    )
    mock_manager.folder_manager.move_emails.return_value = False
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_exception(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="list",
        json=False
    )
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    mock_manager.folder_manager.list_folders.side_effect = Exception("Boom")
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_message')
def test_handle_folder_connect_failed(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="list",
        json=False
    )
    mock_manager.connector.get_imap_connection.return_value = None
    
    handle_folder(args, mock_manager)
    
    mock_render.assert_called_once_with(ANY, type="error", json_output=False)

@patch('cli.render.CLIRenderer.render_folders_table')
def test_handle_folder_list_success_json(mock_render, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="list",
        verbose=False,
        json=True
    )
    mock_manager.folder_manager.list_folders.return_value = ["INBOX", "Sent"]
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_manager.folder_manager.list_folders.assert_called_once()
    mock_render.assert_called_once_with(ANY, "test_acc", verbose=False, json_output=True)
