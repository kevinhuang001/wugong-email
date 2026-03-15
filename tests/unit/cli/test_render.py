import pytest
from unittest.mock import MagicMock, patch
from cli.render import CLIRenderer
from mail.storage_manager import Email

@pytest.fixture
def mock_console():
    with patch('cli.render.console') as mock:
        yield mock

def test_render_header(mock_console):
    CLIRenderer.render_header("Title", "Subtitle")
    assert mock_console.print.call_count == 2

def test_render_email_table_with_email_objects(mock_console):
    emails = [
        Email(
            account_name="test",
            folder="INBOX",
            uid="1",
            sender="Sender",
            sender_email="sender@test.com",
            subject="Subject",
            date="Thu, 14 Mar 2024 12:00:00 +0000",
            seen=False,
            content_type="text/plain",
            content="Content",
            attachments=[]
        )
    ]
    CLIRenderer.render_email_table(emails)
    mock_console.print.assert_called()

def test_render_email_table_with_dicts(mock_console):
    emails = [
        {
            "id": "2",
            "folder": "Archive",
            "from": "Other",
            "from_email": "other@test.com",
            "subject": "Hello\nWorld", # Test cleaning
            "date": "Invalid Date",    # Test invalid date fallback
            "seen": True
        }
    ]
    CLIRenderer.render_email_table(emails)
    mock_console.print.assert_called()

def test_render_email_content_with_email_object(mock_console):
    email = Email(
        account_name="test",
        folder="INBOX",
        uid="1",
        sender="Sender",
        sender_email="sender@test.com",
        subject="Subject",
        date="2024-03-14",
        seen=True,
        content_type="text/plain",
        content="This is the content",
        attachments=["file.txt"]
    )
    CLIRenderer.render_email_content(email, "Test Account")
    mock_console.print.assert_called()

def test_render_email_content_with_dict(mock_console):
    email_dict = {
        "id": "2",
        "subject": "Dict Subject",
        "from": "Dict Sender",
        "from_email": "dict@test.com",
        "date": "2024-03-15",
        "content": "Dict Content",
        "attachments": ["a.pdf", "b.png"],
        "folder": "Trash"
    }
    CLIRenderer.render_email_content(email_dict, "Test Account")
    mock_console.print.assert_called()

def test_render_email_table_empty(mock_console):
    CLIRenderer.render_email_table([])
    # Should still print table and line
    assert mock_console.print.call_count == 2
