import pytest
from unittest.mock import patch
from main import main

@patch('main.logger')
def test_version_arg(mock_logger):
    with patch('sys.argv', ['main.py', '--version']):
        # main() just prints and returns, doesn't exit
        main()
