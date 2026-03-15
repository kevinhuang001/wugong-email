import pytest
import argparse
from unittest.mock import MagicMock, patch
from cli.commands.list import handle_list

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.accounts = [{"friendly_name": "test_acc", "imap_server": "imap.test.com", "imap_port": 993}]
    manager.get_account_by_name.return_value = manager.accounts[0]
    manager.encryption_enabled = False
    manager.config = {"general": {"encrypt_emails": False}}
    return manager

@patch('cli.commands.list.console')
@patch('cli.render.CLIRenderer.render_email_table')
def test_handle_list_success(mock_render, mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        keyword=None,
        from_user=None,
        since=None,
        before=None,
        all=False,
        limit=10,
        local=False,
        password="test_password",
        folder="INBOX",
        sort="date",
        order="desc"
    )
    
    # Mock lister.query_emails
    mock_manager.lister.query_emails.return_value = (
        [{"id": "1", "from": "sender", "subject": "test", "date": "2024-01-01", "seen": True}],
        {"is_offline": False}
    )
    
    handle_list(args, mock_manager)
    
    # Verify lister.query_emails was called
    mock_manager.lister.query_emails.assert_called_once()
    # Verify table was rendered
    assert mock_render.called

@patch('cli.commands.list.console')
def test_handle_list_with_sorting(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        keyword=None,
        from_user=None,
        since=None,
        before=None,
        all=False,
        limit=10,
        local=True,
        password="test_password",
        folder="all",
        sort="subject",
        order="asc"
    )
    
    mock_manager.lister.query_emails.return_value = ([], {"is_offline": True})
    
    handle_list(args, mock_manager)
    
    # Verify sorting parameters passed to query_emails
    mock_manager.lister.query_emails.assert_called_once()
    call_args = mock_manager.lister.query_emails.call_args[1]
    assert call_args['sort_by'] == "subject"
    assert call_args['order'] == "asc"

@patch('cli.commands.list.console')
def test_handle_list_no_accounts(mock_console, mock_manager):
    mock_manager.accounts = []
    args = argparse.Namespace(account="test_acc")
    
    handle_list(args, mock_manager)
    
    assert mock_console.print.called

@patch('cli.commands.list.console')
def test_handle_list_account_not_found(mock_console, mock_manager):
    args = argparse.Namespace(account="non_existent")
    mock_manager.get_account_by_name.return_value = None
    
    handle_list(args, mock_manager)
    
    assert any("not found" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.list.console')
@patch('cli.render.console')
def test_handle_list_query_error(mock_renderer_console, mock_console, mock_manager):
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
    mock_manager.lister.query_emails.side_effect = Exception("Query Failed")
    
    handle_list(args, mock_manager)
    
    # Error is printed to cli.commands.list.console
    assert any("error listing" in str(call).lower() for call in mock_console.print.call_args_list)

@patch('cli.commands.list.console')
@patch('cli.render.console')
def test_handle_list_empty_emails(mock_renderer_console, mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        keyword=None,
        from_user=None,
        since=None,
        before=None,
        all=False,
        limit=10,
        local=True,
        password="test_password"
    )
    mock_manager.lister.query_emails.return_value = ([], {"is_offline": True})
    
    handle_list(args, mock_manager)
    
    # Should still render header and table (even if empty) to renderer console
    assert mock_renderer_console.print.called

@patch('cli.commands.list.console')
@patch('cli.render.console')
def test_handle_list_all_accounts(mock_renderer_console, mock_console, mock_manager):
    args = argparse.Namespace(
        account="all",
        keyword=None,
        from_user=None,
        since=None,
        before=None,
        all=True,
        limit=None,
        local=False,
        password="test_password"
    )
    mock_manager.accounts = [
        {"friendly_name": "acc1"},
        {"friendly_name": "acc2"}
    ]
    mock_manager.lister.query_emails.return_value = ([], {"is_offline": False})
    
    handle_list(args, mock_manager)
    
    assert mock_manager.lister.query_emails.call_count == 2

@patch('cli.commands.list.console')
@patch('cli.render.CLIRenderer.render_header')
def test_handle_list_utf8_not_supported(mock_render_header, mock_console, mock_manager):
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
    mock_manager.lister.query_emails.return_value = (
        [], 
        {"is_fallback": True, "error": "UTF-8 not supported"}
    )
    
    handle_list(args, mock_manager)
    
    # Verify title contains UTF-8 warning
    args, kwargs = mock_render_header.call_args
    title = args[0]
    assert "utf-8 not supported" in title.lower()

@patch('cli.commands.list.config.get_encryption_password')
@patch('cli.commands.list.console')
def test_handle_list_password_cancel(mock_console, mock_get_pass, mock_manager):
    args = argparse.Namespace(account="test_acc", keyword=None, from_user=None, since=None, before=None, all=False, limit=10, local=False)
    mock_manager.encryption_enabled = True
    mock_get_pass.return_value = None
    
    handle_list(args, mock_manager)
    
    mock_get_pass.assert_called_once()
    mock_manager.lister.query_emails.assert_not_called()

@patch('cli.commands.list.console')
@patch('cli.render.CLIRenderer.render_header')
def test_handle_list_with_filters(mock_render_header, mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        keyword="test_keyword",
        from_user="test_from",
        since=None,
        before=None,
        all=False,
        limit=10,
        local=False,
        password="test_password",
        folder="INBOX"
    )
    mock_manager.lister.query_emails.return_value = ([], {"is_offline": False})
    
    handle_list(args, mock_manager)
    
    # Verify filters are rendered in header
    args, kwargs = mock_render_header.call_args
    subtitle = args[1]
    assert "keyword" in subtitle.lower()
    assert "test_keyword" in subtitle.lower()
    assert "from" in subtitle.lower()
    assert "test_from" in subtitle.lower()

@patch('cli.commands.list.console')
def test_handle_list_with_status(mock_console, mock_manager):
    args = argparse.Namespace(
        account="test_acc",
        keyword=None,
        from_user=None,
        since=None,
        before=None,
        all=False,
        limit=10,
        local=False,
        password="test_password",
        folder="INBOX"
    )
    mock_manager.lister.query_emails.return_value = ([], {"is_offline": False})
    
    with patch('sys.stdin.isatty', return_value=True):
        handle_list(args, mock_manager)
    
    # Verify console.status was called
    assert mock_console.status.called
