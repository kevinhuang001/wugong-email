import pytest
import json
from unittest.mock import patch
from tests.conftest import run_wugong_command

def test_upgrade_command(mail_config):
    """Test the 'upgrade' command."""
    config_path = mail_config["config_path"]
    password = mail_config["master_password"]
    
    # upgrade --force
    # We mock the upgrade process to avoid actual network calls or system changes.
    with patch("main.handle_upgrade") as mock_handle:
        def side_effect(args, manager):
            from cli.render import CLIRenderer
            CLIRenderer.render_message("Upgraded successfully", type="success", json_output=getattr(args, "json", False))
            
        mock_handle.side_effect = side_effect
        
        upgrade_args = [
            "upgrade",
            "--force"
        ]
        
        output = run_wugong_command(upgrade_args, config_path, password)
        res = json.loads(output)
        
        assert res.get("status") == "success"
        mock_handle.assert_called_once()
