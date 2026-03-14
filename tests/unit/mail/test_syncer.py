import pytest
import imaplib
from unittest.mock import MagicMock, patch
from datetime import datetime
from mail.syncer import MailSyncer

@pytest.fixture
def mock_connector():
    return MagicMock()

@pytest.fixture
def mock_storage_manager():
    return MagicMock()

@pytest.fixture
def syncer(mock_connector, mock_storage_manager):
    return MailSyncer(
        connector=mock_connector,
        storage_manager=mock_storage_manager,
        config={},
        save_config_callback=MagicMock()
    )

def test_build_search_query_initial(syncer):
    query = syncer._build_search_query(None, True, 20, {})
    assert query == ["ALL"]

def test_build_search_query_with_criteria(syncer):
    criteria = {
        "keyword": "test",
        "from": "alice@example.com",
        "since": "2024-01-01"
    }
    query = syncer._build_search_query(criteria, False, 20, {})
    assert "TEXT" in query
    assert "test" in query
    assert "FROM" in query
    assert "alice@example.com" in query
    assert "SINCE" in query
    assert "01-Jan-2024" in query

def test_imap_search_ascii_success(syncer):
    mock_mail = MagicMock()
    mock_mail.uid.return_value = ("OK", [b"1 2 3"])
    
    res, data = syncer._imap_search(mock_mail, ["ALL"])
    
    assert res == "OK"
    assert data == [b"1 2 3"]
    mock_mail.uid.assert_called_with('search', None, "ALL")

@patch('mail.syncer.logger')
def test_imap_search_utf8_fallback(mock_logger, syncer):
    mock_mail = MagicMock()
    # First call (ASCII) fails
    mock_mail.uid.side_effect = [Exception("UTF-8 required"), ("OK", [b"1 2 3"])]
    mock_mail._utf8_enabled = True
    
    res, data = syncer._imap_search(mock_mail, ["TEXT", "test_utf8"])
    
    assert res == "OK"
    assert data == [b"1 2 3"]


def test_sync_emails_success(syncer, mock_connector, mock_storage_manager):
    account = {"friendly_name": "test_acc"}
    mock_storage_manager.get_last_sync_info.return_value = {"time": "Never", "uid": "0"}
    
    mock_mail = MagicMock()
    mock_connector.get_imap_connection.return_value = mock_mail
    mock_mail.select.return_value = ("OK", [b"10"])
    mock_mail.uid.return_value = ("OK", [b"1 2 3"])
    
    # Mock internal sync
    with patch.object(syncer, '_sync_emails_internal', return_value=[]):
        emails, status = syncer.sync_emails(account, "pwd", limit=5)
        
        assert status["is_offline"] is False
    mock_storage_manager.update_sync_info.assert_called_once()
    mock_storage_manager.get_emails_from_cache.assert_called_once()

def test_imap_search_ascii_error_fallback(syncer):
    mock_mail = MagicMock()
    # ASCII fails, should fall back to UTF-8
    mock_mail.uid.side_effect = [imaplib.IMAP4.error("Search failed"), ("OK", [b"1 2 3"])]
    mock_mail._utf8_enabled = False
    
    res, data = syncer._imap_search(mock_mail, ["TEXT", "test"])
    
    assert res == "OK"
    assert data == [b"1 2 3"]

def test_imap_search_utf8_not_enabled_fallback(syncer):
    mock_mail = MagicMock()
    # has_non_ascii will be True
    # _utf8_enabled is False
    # should try CHARSET UTF-8
    mock_mail.uid.return_value = ("OK", [b"4 5 6"])
    mock_mail._utf8_enabled = False
    
    res, data = syncer._imap_search(mock_mail, ["TEXT", "test_utf8"])
    
    assert res == "OK"
    assert data == [b"4 5 6"]
    # Verify it called with CHARSET UTF-8
    mock_mail.uid.assert_called_with('SEARCH', 'CHARSET', 'UTF-8', 'TEXT', "test_utf8".encode('utf-8'))


def test_sync_emails_utf8_unsupported_error(syncer, mock_connector, mock_storage_manager):
    account = {"friendly_name": "test_acc"}
    mock_storage_manager.get_last_sync_info.return_value = {"time": "Never", "uid": "0"}
    
    mock_mail = MagicMock()
    mock_connector.get_imap_connection.return_value = mock_mail
    mock_mail.select.return_value = ("OK", [b"10"])
    
    # Mock _imap_search to raise UTF-8 not supported error
    with patch.object(syncer, '_imap_search', side_effect=Exception("UTF-8 not supported")):
        emails, status = syncer.sync_emails(account, "pwd", limit=5)
        
        assert status["is_offline"] is True
        assert "UTF-8 not supported" in status["error"]

def test_build_search_query_with_sync_info_time(syncer):
    sync_info = {"time": "2024-03-14 12:00:00", "uid": "100"}
    query = syncer._build_search_query(None, False, 0, sync_info)
    assert "SINCE" in query
    assert "14-Mar-2024" in query

def test_format_date_invalid(syncer):
    # Should return original string if format is invalid
    assert syncer._format_date("invalid-date") == "invalid-date"

def test_sync_emails_internal_status_mismatch(syncer, mock_storage_manager):
    mock_mail = MagicMock()
    uids = [b"1", b"2"]
    account_name = "test_acc"
    folder = "INBOX"
    
    # Mock cached statuses: 1 is seen, 2 is unseen
    mock_storage_manager.get_cached_statuses.return_value = {"1": True, "2": False}
    
    # Mock server statuses: 1 is unseen, 2 is seen (mismatch)
    with patch.object(syncer, '_fetch_server_statuses', return_value={"1": False, "2": True}):
        # Mock fetch for content (though it shouldn't be called for 1 and 2 if they are in cache)
        # Wait, if they are in cache but status mismatch, we update status, not fetch content.
        syncer._sync_emails_internal(mock_mail, account_name, folder, uids, "pwd", None)
        
        # Check update_seen_status calls
        assert mock_storage_manager.update_seen_status.call_count == 2
        mock_storage_manager.update_seen_status.assert_any_call(account_name, "1", False, folder)
        mock_storage_manager.update_seen_status.assert_any_call(account_name, "2", True, folder)

def test_fetch_server_statuses_multiple_batches(syncer):
    mock_mail = MagicMock()
    # 600 UIDs to trigger 2 batches (batch_size=500)
    uids = [str(i).encode() for i in range(1, 601)]
    
    # Mock responses for 2 batches
    # Each response is a list of tuples (response_text, content)
    resp1 = [(b"1 (FLAGS (\\Seen) UID 1)", b""), (b"2 (FLAGS () UID 2)", b"")]
    resp2 = [(b"501 (FLAGS (\\Seen) UID 501)", b"")]
    mock_mail.uid.side_effect = [("OK", resp1), ("OK", resp2)]
    
    statuses = syncer._fetch_server_statuses(mock_mail, uids)
    
    assert statuses["1"] is True
    assert statuses["2"] is False
    assert statuses["501"] is True
    assert mock_mail.uid.call_count == 2
