import pytest
from unittest.mock import MagicMock, patch
from mail.reader import MailReader
import imaplib

@pytest.fixture
def mock_managers():
    auth_manager = MagicMock()
    storage_manager = MagicMock()
    config = {}
    save_config_callback = MagicMock()
    return auth_manager, storage_manager, config, save_config_callback

def test_mail_reader_init(mock_managers):
    auth_manager, storage_manager, config, save_config_callback = mock_managers
    reader = MailReader(auth_manager, storage_manager, config, save_config_callback)
    assert reader.auth_manager == auth_manager
    assert reader.storage_manager == storage_manager

@patch('imaplib.IMAP4_SSL')
def test_query_emails_offline_on_timeout(mock_imap, mock_managers):
    auth_manager, storage_manager, config, save_config_callback = mock_managers
    reader = MailReader(auth_manager, storage_manager, config, save_config_callback)
    
    # Mock account and auth
    account = {
        'friendly_name': 'test_acc',
        'imap_server': 'imap.test.com',
        'imap_port': 993,
        'login_method': 'Account/Password'
    }
    auth_password = "password"
    auth_manager.decrypt_account_auth.return_value = {'username': 'user', 'password': 'pass'}
    storage_manager.get_last_sync_info.return_value = {'time': '2023-01-01 00:00:00'}
    
    # Mock imaplib to raise timeout
    import socket
    mock_imap.side_effect = socket.timeout("Connection timed out")
    
    # Mock storage_manager.get_emails_from_cache
    storage_manager.get_emails_from_cache.return_value = [{"id": 1, "subject": "Test Cache"}]
    
    emails, metadata = reader.query_emails(account, auth_password)
    
    assert metadata['is_offline'] is True
    assert "timeout" in metadata['error']
    assert emails[0]['subject'] == "Test Cache"

@patch('imaplib.IMAP4_SSL')
def test_query_emails_success(mock_imap, mock_managers):
    auth_manager, storage_manager, config, save_config_callback = mock_managers
    reader = MailReader(auth_manager, storage_manager, config, save_config_callback)
    
    account = {
        'friendly_name': 'test_acc',
        'imap_server': 'imap.test.com',
        'imap_port': 993,
        'login_method': 'Account/Password'
    }
    auth_password = "password"
    auth_manager.decrypt_account_auth.return_value = {'username': 'user', 'password': 'pass'}
    storage_manager.get_last_sync_info.return_value = {'time': '2023-01-01 00:00:00'}
    
    # Mock IMAP instance
    mock_mail = MagicMock()
    mock_imap.return_value = mock_mail
    mock_mail.select.return_value = ("OK", [b"100"])
    
    # Mock search result
    search_res = ("OK", [b"1 2"])
    
    # Mock fetch results (must be a list containing a tuple for each UID)
    # The code reverses view_uids, so it will fetch UID 2 then UID 1
    fetch_2 = ("OK", [(b"2 (FLAGS (\\Seen) BODY[HEADER.FIELDS (SUBJECT FROM DATE)] {50}", b"Subject: Test 2\r\nFrom: user2@test.com\r\nDate: Mon, 2 Jan 2024 00:00:00 +0000")])
    fetch_1 = ("OK", [(b"1 (FLAGS (\\Seen) BODY[HEADER.FIELDS (SUBJECT FROM DATE)] {50}", b"Subject: Test 1\r\nFrom: user1@test.com\r\nDate: Mon, 1 Jan 2024 00:00:00 +0000")])
    
    mock_mail.uid.side_effect = [search_res, fetch_2, fetch_1]
    
    emails, metadata = reader.query_emails(account, auth_password)
    
    assert metadata['is_offline'] is False
    assert len(emails) == 2
    assert emails[0]['subject'] == "Test 2" # Because of list(reversed(view_uids))
