import pytest
from unittest.mock import MagicMock, patch
from mail.auth import AuthManager

@pytest.fixture
def auth_manager():
    return AuthManager(encryption_enabled=True, salt="test_salt")

@patch('mail.auth.decrypt_data')
def test_decrypt_account_auth(mock_decrypt, auth_manager):
    mock_decrypt.side_effect = lambda data, pwd, salt: f"decrypted_{data}"
    
    account = {
        "friendly_name": "test_acc",
        "auth": {
            "password": "encrypted_pass",
            "username": "user123" # Not in sensitive_keys, shouldn't be decrypted
        }
    }
    password = "master_password"
    
    decrypted = auth_manager.decrypt_account_auth(account, password)
    
    assert decrypted["password"] == "decrypted_encrypted_pass"
    assert decrypted["username"] == "user123"
    mock_decrypt.assert_called_once_with("encrypted_pass", password, "test_salt")

@patch('requests.post')
@patch('mail.auth.encrypt_data')
def test_refresh_oauth2_token(mock_encrypt, mock_post, auth_manager):
    # Mock successful response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_access",
        "refresh_token": "new_refresh"
    }
    mock_post.return_value = mock_response
    
    mock_encrypt.side_effect = lambda data, pwd, salt: f"encrypted_{data}"
    
    account = {
        "friendly_name": "test_acc",
        "auth": {
            "client_id": "cid",
            "client_secret": "cs",
            "refresh_token": "old_refresh",
            "token_url": "https://token.url"
        }
    }
    auth = {
        "client_id": "cid",
        "client_secret": "cs",
        "refresh_token": "old_refresh",
        "token_url": "https://token.url"
    }
    config = {"accounts": [account]}
    
    new_token = auth_manager.refresh_oauth2_token(account, auth, "pwd", config)
    
    assert new_token == "new_access"
    assert account["auth"]["access_token"] == "encrypted_new_access"
    assert account["auth"]["refresh_token"] == "encrypted_new_refresh"
