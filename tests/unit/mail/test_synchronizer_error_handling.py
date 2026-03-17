import pytest
from unittest.mock import MagicMock, patch
from mail.synchronizer import MailSynchronizer
from mail.storage_manager import Email

@pytest.fixture
def mock_syncer():
    connector = MagicMock()
    storage_manager = MagicMock()
    config = {}
    save_callback = MagicMock()
    return MailSynchronizer(connector, storage_manager, config, save_callback)

def test_sync_emails_internal_saves_on_exception(mock_syncer):
    # Setup
    mail = MagicMock()
    account_name = "test_acc"
    folder = "INBOX"
    uids = [b"1", b"2", b"3"]
    auth_password = "password"
    
    # Mock storage_manager
    mock_syncer.storage_manager.get_cached_statuses.return_value = {}
    
    # Mock _fetch_server_statuses
    with patch.object(MailSynchronizer, '_fetch_server_statuses', return_value={"1": False, "2": False, "3": False}):
        # Mock mail.uid to succeed twice then raise exception
        def side_effect(cmd, uid, msg_type):
            if uid == b"3": # reversed(uids) starts with 3
                return "OK", [(None, b"email content 3")]
            if uid == b"2":
                raise Exception("Network error")
            return "OK", [(None, b"email content 1")]
            
        mail.uid.side_effect = side_effect
        
        # Mock MailParser
        with patch('mail.parser.MailParser.parse_full_email') as mock_parser:
            mock_parser.return_value = Email(
                account_name=account_name,
                folder=folder,
                uid="3",
                subject="S3",
                sender="U3",
                sender_email="E3",
                date="D3",
                seen=False,
                content_type="text/plain",
                content="C3",
                attachments=[]
            )
            
            # Execute and expect exception
            with pytest.raises(Exception, match="Network error"):
                mock_syncer._sync_emails_internal(mail, account_name, folder, uids, auth_password, None)
            
            # Verify save_emails_to_cache was called even though an exception occurred
            mock_syncer.storage_manager.save_emails_to_cache.assert_called_once()
            saved_emails = mock_syncer.storage_manager.save_emails_to_cache.call_args[0][2]
            assert len(saved_emails) == 1
            assert saved_emails[0]['id'] == "3"

def test_sync_emails_saves_on_interrupt(mock_syncer):
    # Setup
    account = {"friendly_name": "test_acc"}
    auth_password = "password"
    folder = "INBOX"
    
    # Mock storage_manager
    mock_syncer.storage_manager.get_last_sync_info.return_value = {"time": "Never", "uid": "0"}
    
    # Mock connector
    mock_mail = MagicMock()
    mock_syncer.connector.get_imap_connection.return_value = mock_mail
    mock_mail.select.return_value = ("OK", [b"123"])
    
    # Mock _imap_search
    with patch.object(MailSynchronizer, '_imap_search', return_value=("OK", [b"1 2 3"])):
        # Mock _get_uids_to_process
        with patch.object(MailSynchronizer, '_get_uids_to_process', return_value=[b"1", b"2", b"3"]):
            # Mock _sync_emails_internal to raise KeyboardInterrupt
            with patch.object(MailSynchronizer, '_sync_emails_internal', side_effect=KeyboardInterrupt()):
                
                # Execute and expect KeyboardInterrupt
                with pytest.raises(KeyboardInterrupt):
                    mock_syncer.sync_emails(account, auth_password)
                
                # Verify finally blocks in sync_emails (mail.close/logout) were called
                mock_mail.close.assert_called_once()
                mock_mail.logout.assert_called_once()
