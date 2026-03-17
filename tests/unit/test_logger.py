import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from logger import setup_logger, update_console_level

def test_setup_logger_basic():
    logger = setup_logger("test_logger")
    assert logger.name == "wugong.test_logger"
    # The child logger might have level NOTSET (0) but its parent 'wugong' should have DEBUG
    root_logger = logging.getLogger("wugong")
    assert root_logger.level == logging.DEBUG

def test_setup_logger_existing():
    # Calling setup_logger twice with same name should return same logger
    logger1 = setup_logger("test_dup")
    logger2 = setup_logger("test_dup")
    assert logger1 is logger2

@patch('logging.FileHandler')
@patch('pathlib.Path.mkdir')
def test_setup_logger_handlers(mock_mkdir, mock_file_handler):
    # Setup mocks
    mock_file_handler.return_value = MagicMock()
    
    # Reset the root logger handlers for testing
    root_logger = logging.getLogger("wugong")
    old_handlers = root_logger.handlers[:]
    root_logger.handlers = []
    
    try:
        setup_logger("new_logger")
        # Should have RichHandler and FileHandler
        assert len(root_logger.handlers) >= 1
    finally:
        # Restore handlers
        root_logger.handlers = old_handlers

def test_update_console_level():
    root_logger = logging.getLogger("wugong")
    # Add a mock stream handler
    mock_handler = MagicMock(spec=logging.StreamHandler)
    # Important: it shouldn't be a FileHandler for update_console_level to pick it
    mock_handler.__class__ = logging.StreamHandler
    root_logger.addHandler(mock_handler)
    
    try:
        update_console_level(logging.ERROR)
        mock_handler.setLevel.assert_called_with(logging.ERROR)
    finally:
        # Cleanup
        root_logger.removeHandler(mock_handler)
