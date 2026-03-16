import pytest
import json
import os
from unittest.mock import patch
from tests.conftest import run_wugong_command

def test_uninstall_command(mail_config):
    """Test the 'uninstall' command."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # uninstall --keep-data
    # We mock the uninstall process to avoid actual system changes.
    with patch("main.handle_uninstall") as mock_handle:
        def side_effect(args, manager):
            from cli.render import CLIRenderer
            CLIRenderer.render_message("Uninstalled successfully", type="success", json_output=getattr(args, "json", False))
            
        mock_handle.side_effect = side_effect
        
        uninstall_args = [
            "uninstall",
            "--keep-data"
        ]
        
        output = run_wugong_command(uninstall_args, config_path, password)
        res = json.loads(output)
        
        assert res.get("status") == "success"
        mock_handle.assert_called_once()
