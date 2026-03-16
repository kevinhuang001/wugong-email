import pytest
import os
import sys
import subprocess
import time
import socket
import shutil
import base64
import imaplib
import io
import re
import json
from unittest.mock import patch
from email.message import EmailMessage
from pathlib import Path

# Add the root directory and tests directory to sys.path to import modules
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))
from main import main
from crypto_utils import encrypt_data
from test_utils import init_mailbox, clear_mailbox
from logger import disable_logging, enable_logging, logger

def run_wugong_command(args, config_path, password):
    """Run wugong command with non-interactive and json output."""
    full_args = ["main.py"] + args + ["--encryption-password", password, "--non-interactive", "--json"]
    
    # Disable logging to avoid stderr/stdout pollution during tests
    disable_logging()
    
    with patch("sys.argv", full_args), \
         patch.dict(os.environ, {"WUGONG_CONFIG": str(config_path)}), \
         patch("sys.stdout", new=io.StringIO()) as mock_stdout, \
         patch("sys.stderr", new=io.StringIO()) as mock_stderr:
        try:
            main()
        except SystemExit as e:
            if e.code != 0:
                raise RuntimeError(f"Wugong exited with code {e.code}. Output: {mock_stdout.getvalue()}")
        raw_output = mock_stdout.getvalue()
        raw_error = mock_stderr.getvalue()

    # Restore logging after command
    enable_logging()
    
    # Try to extract the JSON part from the output
    # Find all top-level JSON blocks (non-overlapping)
    json_blocks = []
    i = 0
    while i < len(raw_output):
        if raw_output[i] in '[{':
            start = i
            # Try to find the matching end bracket
            # We use a simple stack-based approach to find the matching bracket
            stack = []
            for j in range(i, len(raw_output)):
                char = raw_output[j]
                if char in '[{':
                    # Simplified: we don't distinguish [ vs { for matching here
                    # because we just want the outer-most one
                    stack.append(char)
                elif char in ']}':
                    if stack:
                        stack.pop()
                        if not stack:
                            # Found a potential top-level block
                            potential_json = raw_output[start:j+1]
                            try:
                                json.loads(potential_json)
                                json_blocks.append(potential_json)
                                i = j # Move to the end of this block
                                break
                            except json.JSONDecodeError:
                                # Not valid JSON, keep looking
                                pass
            i += 1
        else:
            i += 1
            
    # If no JSON found, return the raw output (it might be an error or empty)
    # with open("test_output_debug.log", "a") as f:
    #     f.write(f"\nCOMMAND: {args}\n")
    #     f.write(f"RAW OUTPUT: {raw_output}\n")
    #     f.write(f"JSON BLOCKS: {json_blocks}\n")
    
    # Concatenate multiple JSON blocks if they exist (rare, but for safety)
    if len(json_blocks) > 1:
        # If it's a list of dicts, we might want to merge them, but for tests,
        # usually the first one is the main result.
        # Let's return the first one but log a warning.
        pass

    if not json_blocks:
        print(f"DEBUG: No JSON found in output. RAW: {raw_output}")
    return json_blocks[0] if json_blocks else raw_output

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

@pytest.fixture(scope="session")
def mail_server():
    """
    Check if Greenmail server is running.
    If not running, raise an error immediately.
    """
    smtp_port = 3025
    imap_port = 3143
    
    # Check if ports are open
    if not (is_port_open(smtp_port) and is_port_open(imap_port)):
        raise RuntimeError(
            "\nGreenmail server is not running!\n"
            "Please start it manually before running integration tests:\n"
            "docker run -it --rm -p 3025:3025 -p 3143:3143 greenmail/standalone:2.0.0"
        )

    yield {
        "smtp_port": smtp_port,
        "imap_port": imap_port
    }

@pytest.fixture
def mail_config(tmp_path, mail_server):
    """
    Create a temporary wugong config that points to the Greenmail server.
    """
    config_dir = tmp_path / ".wugong"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    db_path = config_dir / "emails.db"
    
    master_password = "test_password"
    salt_bytes = b"test_salt_123456" # 16 bytes
    salt_b64 = base64.b64encode(salt_bytes).decode()
    
    # Greenmail credentials: username is the email, password is the same as username by default
    # but we can use 'password' as password for 'user1@example.com'
    # Actually, Greenmail default configuration for standalone often accepts ANY password
    # if it's not pre-configured, but for 'user1@example.com', 'password' is a safe bet
    # if we haven't set up specific users. 
    # WAIT: Greenmail standalone 2.0.0 by default might not have users.
    # Let's use 'password' for both and see. 
    encrypted_pw1 = encrypt_data("password", master_password, salt_bytes)
    encrypted_pw2 = encrypt_data("password", master_password, salt_bytes)
    
    smtp_port = mail_server["smtp_port"]
    imap_port = mail_server["imap_port"]
    
    content = f"""
[general]
encryption_enabled = true
salt = "{salt_b64}"
database_path = "{db_path}"

[[accounts]]
    friendly_name = "user1"
    email = "user1@example.com"
    imap_server = "127.0.0.1"
    imap_port = {imap_port}
    imap_tls_method = "Plain"
    smtp_server = "127.0.0.1"
    smtp_port = {smtp_port}
    smtp_tls_method = "Plain"
    login_method = "Account/Password"
    auth_method = "Account/Password"
    [accounts.auth]
    username = "user1"
    password = "{encrypted_pw1}"

[[accounts]]
    friendly_name = "user2"
    email = "user2@example.com"
    imap_server = "127.0.0.1"
    imap_port = {imap_port}
    imap_tls_method = "Plain"
    smtp_server = "127.0.0.1"
    smtp_port = {smtp_port}
    smtp_tls_method = "Plain"
    login_method = "Account/Password"
    auth_method = "Account/Password"
    [accounts.auth]
    username = "user2"
    password = "{encrypted_pw2}"
"""
    with open(config_path, "w") as f:
        f.write(content)
    
    # Initialize both mailboxes on the server
    init_mailbox("user1", "password", imap_port)
    init_mailbox("user2", "password", imap_port)
    
    yield {
        "config_dir": config_dir,
        "config_path": config_path,
        "db_path": db_path,
        "master_password": master_password,
        "accounts": ["user1", "user2"]
    }

@pytest.fixture(autouse=True)
def cleanup_mailboxes(mail_server):
    """
    Automatically clear mailboxes after each test.
    """
    yield
    imap_port = mail_server["imap_port"]
    logger.debug("Auto-clearing mailboxes after test...")
    try:
        clear_mailbox("user1", "password", imap_port)
    except Exception as e:
        logger.debug(f"Failed to clear user1: {e}")
    try:
        clear_mailbox("user2", "password", imap_port)
    except Exception as e:
        logger.debug(f"Failed to clear user2: {e}")
