import pytest
import argparse
from unittest.mock import MagicMock, patch
from cli.commands.folder import handle_folder

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.commands.folder.console')
def test_handle_folder_list_success(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="list"
    )
    mock_manager.folder_manager.list_folders.return_value = ["INBOX", "Sent"]
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_manager.folder_manager.list_folders.assert_called_once()
    assert mock_console.print.called

@patch('cli.commands.folder.console')
def test_handle_folder_create_success(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="create",
        name="NewFolder"
    )
    mock_manager.folder_manager.create_folder.return_value = True
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_manager.folder_manager.create_folder.assert_called_once()
    assert mock_console.print.called

@patch('questionary.confirm')
@patch('cli.commands.folder.console')
def test_handle_folder_delete_success(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="delete",
        name="OldFolder"
    )
    mock_confirm.return_value.ask.return_value = True
    mock_manager.folder_manager.delete_folder.return_value = True
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_manager.folder_manager.delete_folder.assert_called_once()
    assert mock_console.print.called

@patch('cli.commands.folder.console')
def test_handle_folder_move_success(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="move",
        id="1,2,3",
        src="INBOX",
        dest="Archive"
    )
    mock_manager.folder_manager.move_emails.return_value = True
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    mock_manager.folder_manager.move_emails.assert_called_once_with(
        mock_manager.connector.get_imap_connection.return_value,
        ["1", "2", "3"], "INBOX", "Archive"
    )
    assert mock_console.print.called

@patch('cli.commands.folder.console')
def test_handle_folder_account_not_found(mock_console, mock_manager):
    args = argparse.Namespace(
        account="non_existent",
        folder_command="list"
    )
    mock_manager.get_account_by_name.return_value = None
    
    handle_folder(args, mock_manager)
    
    assert any("not found" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.folder.config.get_encryption_password')
@patch('cli.commands.folder.console')
def test_handle_folder_password_cancel(mock_console, mock_get_pass, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="list")
    mock_manager.encryption_enabled = True
    mock_get_pass.return_value = None
    
    handle_folder(args, mock_manager)
    
    mock_get_pass.assert_called_once()
    mock_manager.connector.get_imap_connection.assert_not_called()

@patch('cli.commands.folder.console')
def test_handle_folder_create_no_name(mock_console, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="create", name=None)
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert any("folder name is required" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.folder.console')
def test_handle_folder_delete_no_name(mock_console, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="delete", name=None)
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert any("folder name is required" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('questionary.confirm')
@patch('cli.commands.folder.console')
def test_handle_folder_delete_failed(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="delete", name="OldFolder")
    mock_confirm.return_value.ask.return_value = True
    mock_manager.folder_manager.delete_folder.return_value = False
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert any("failed to delete folder" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.folder.console')
def test_handle_folder_move_no_id_or_dest(mock_console, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="move", id=None, dest=None)
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert any("id and destination folder are required" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.folder.console')
def test_handle_folder_logout_exception(mock_console, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="list")
    mock_mail = MagicMock()
    mock_mail.logout.side_effect = Exception("Logout Error")
    mock_manager.connector.get_imap_connection.return_value = mock_mail
    mock_manager.folder_manager.list_folders.return_value = []
    
    handle_folder(args, mock_manager)
    
    # Should not raise exception
    mock_mail.logout.assert_called_once()

@patch('cli.commands.folder.console')
def test_handle_folder_general_exception(mock_console, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="list")
    mock_manager.connector.get_imap_connection.side_effect = Exception("General Error")
    
    handle_folder(args, mock_manager)
    
    assert any("error: general error" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.folder.console')
def test_handle_folder_unknown_command(mock_console, mock_manager):
    args = argparse.Namespace(account="test_acc", folder_command="unknown")
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert any("unknown folder command" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.folder.console')
def test_handle_folder_create_failed(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="create",
        name="NewFolder"
    )
    mock_manager.folder_manager.create_folder.return_value = False
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert any("failed to create" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('questionary.confirm')
@patch('cli.commands.folder.console')
def test_handle_folder_delete_cancel(mock_console, mock_confirm, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="delete",
        name="OldFolder"
    )
    mock_confirm.return_value.ask.return_value = False
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert mock_manager.folder_manager.delete_folder.call_count == 0

@patch('cli.commands.folder.console')
def test_handle_folder_move_failed(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="move",
        id="1",
        src="INBOX",
        dest="Archive"
    )
    mock_manager.folder_manager.move_emails.return_value = False
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert any("failed to move" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.folder.console')
def test_handle_folder_unknown_command(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="unknown"
    )
    mock_manager.connector.get_imap_connection.return_value = MagicMock()
    
    handle_folder(args, mock_manager)
    
    assert any("unknown folder command" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.folder.console')
def test_handle_folder_exception(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="list"
    )
    mock_manager.connector.get_imap_connection.side_effect = Exception("Boom")
    
    handle_folder(args, mock_manager)
    
    assert any("error: boom" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.folder.console')
def test_handle_folder_connect_failed(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        folder_command="list"
    )
    mock_manager.connector.get_imap_connection.return_value = None
    
    handle_folder(args, mock_manager)
    
    assert any("failed to connect to imap server" in str(call).lower() for call in mock_console.print.call_args_list)
