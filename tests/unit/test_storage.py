import pytest
import sqlite3
import os
from mail.storage import StorageManager

@pytest.fixture
def storage_manager(tmp_path):
    db_path = tmp_path / "test.db"
    return StorageManager(str(db_path), encrypt_emails=False, encryption_enabled=False, salt="test_salt")

def test_storage_manager_init(storage_manager):
    assert os.path.exists(storage_manager.db_path)
    # Check if tables are created
    conn = sqlite3.connect(storage_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
    assert cursor.fetchone() is not None
    conn.close()

def test_update_get_sync_info(storage_manager):
    account = "test_acc"
    storage_manager.update_sync_info(account, "2024-01-01 10:00:00", "123")
    info = storage_manager.get_last_sync_info(account)
    assert info["time"] == "2024-01-01 10:00:00"
    assert info["uid"] == "123"

def test_get_sync_info_never(storage_manager):
    info = storage_manager.get_last_sync_info("non_existent")
    assert info["time"] == "Never"
    assert info["uid"] == "0"

def test_save_get_emails_from_cache(storage_manager):
    account = "test_acc"
    emails = [{
        "id": "1",
        "from": "user@test.com",
        "from_email": "user@test.com",
        "subject": "Test Subject",
        "content": "Test Content",
        "content_type": "text/plain",
        "date": "2024-01-01"
    }]
    storage_manager.save_emails_to_cache(account, emails, "pwd")
    
    # Test getting from cache
    cached = storage_manager.get_emails_from_cache(account, limit=10, search_criteria={}, password="pwd")
    assert len(cached) == 1
    assert cached[0]["subject"] == "Test Subject"
    assert cached[0]["id"] == "1"

def test_search_criteria_in_cache(storage_manager):
    account = "test_acc"
    emails = [
        {"id": "1", "from": "A", "from_email": "a@test.com", "subject": "Hello", "content": "C1", "content_type": "text/plain", "date": "2024-01-01"},
        {"id": "2", "from": "B", "from_email": "b@test.com", "subject": "World", "content": "C2", "content_type": "text/plain", "date": "2024-01-01"}
    ]
    storage_manager.save_emails_to_cache(account, emails, "pwd")
    
    # Search by keyword
    cached = storage_manager.get_emails_from_cache(account, limit=10, search_criteria={"keyword": "Hello"}, password="pwd")
    assert len(cached) == 1
    assert cached[0]["subject"] == "Hello"
    
    # Search by from
    cached = storage_manager.get_emails_from_cache(account, limit=10, search_criteria={"from": "b@test.com"}, password="pwd")
    assert len(cached) == 1
    assert cached[0]["from_email"] == "b@test.com"
