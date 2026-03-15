import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import config

def test_get_config_path_env():
    with patch.dict(os.environ, {"WUGONG_CONFIG": "/tmp/custom_config.toml"}):
        assert config.get_config_path() == Path("/tmp/custom_config.toml")

def test_get_config_path_default():
    with patch.dict(os.environ, {}, clear=True):
        # We don't want to rely on the actual home dir in tests
        with patch('pathlib.Path.home', return_value=Path("/home/user")):
            with patch('pathlib.Path.exists', return_value=False):
                assert config.get_config_path() == Path("/home/user/.config/wugong/config.toml")

@patch('toml.load')
@patch('pathlib.Path.exists', return_value=True)
def test_load_config_success(mock_exists, mock_toml_load):
    mock_toml_load.return_value = {"general": {"encryption_enabled": True}}
    cfg = config.load_config("/tmp/test.toml")
    assert cfg["general"]["encryption_enabled"] is True

@patch('toml.dump')
@patch('pathlib.Path.mkdir')
@patch('builtins.open')
def test_save_config(mock_open, mock_mkdir, mock_toml_dump):
    cfg = {"test": "data"}
    config.save_config(cfg, "/tmp/save_test.toml")
    mock_mkdir.assert_called_once()
    mock_toml_dump.assert_called_once_with(cfg, mock_open.return_value.__enter__.return_value)

def test_get_salt_from_config():
    cfg = {"general": {"salt": "dGVzdF9zYWx0"}} # "test_salt" in base64
    assert config.get_salt(cfg) == b"test_salt"

def test_get_salt_default():
    cfg = {"general": {}}
    assert config.get_salt(cfg) == b"wugong-default-salt"

@patch('questionary.password')
@patch('sys.stdin.isatty', return_value=True)
def test_get_encryption_password_prompt(mock_isatty, mock_password):
    mock_password.return_value.ask.return_value = "secret"
    pwd = config.get_encryption_password()
    assert pwd == "secret"
