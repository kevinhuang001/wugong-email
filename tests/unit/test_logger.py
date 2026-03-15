import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from logger import setup_logger, update_console_level

def test_setup_logger_basic():
    logger = setup_logger("test_logger")
    assert logger.name == "wugong.test_logger"
    assert logger.level == logging.DEBUG

def test_setup_logger_existing():
    # Calling setup_logger twice with same name should return same logger
    logger1 = setup_logger("test_dup")
    logger2 = setup_logger("test_dup")
    assert logger1 is logger2

@patch('logging.StreamHandler')
@patch('logging.FileHandler')
@patch('pathlib.Path.mkdir')
def test_setup_logger_handlers(mock_mkdir, mock_file_handler, mock_stream_handler):
    # Setup mocks
    mock_file_handler.return_value = MagicMock()
    mock_stream_handler.return_value = MagicMock()
    
    # We need to make sure the root wugong logger doesn't have handlers for this test
    with patch('logging.getLogger') as mock_get_logger:
        mock_root = MagicMock()
        mock_root.handlers = []
        mock_target = MagicMock()
        mock_target.handlers = []
        mock_get_logger.side_effect = lambda name: mock_root if name == "wugong" else mock_target
        
        setup_logger("new_logger")
        
        assert mock_target.addHandler.call_count >= 1

def test_update_console_level():
    root_logger = logging.getLogger("wugong")
    # Add a mock stream handler
    mock_handler = MagicMock(spec=logging.StreamHandler)
    # Important: it shouldn't be a FileHandler for update_console_level to pick it
    mock_handler.__class__ = logging.StreamHandler
    root_logger.addHandler(mock_handler)
    
    update_console_level(logging.ERROR)
    mock_handler.setLevel.assert_called_with(logging.ERROR)
    
    # Cleanup
    root_logger.removeHandler(mock_handler)
