import pytest
import json
import os
from tests.conftest import run_wugong_command

def test_version_option(mail_config):
    """Test the --version option."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # Use run_wugong_command which adds --json and --non-interactive
    output = run_wugong_command(["--version"], config_path, password)
    res = json.loads(output)
    
    # Should contain version string
    assert "version" in res
    assert res["status"] == "info"
