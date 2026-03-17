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
os.environ["WUGONG_TESTING"] = "1"
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
        s.settimeout(0.5)
        # Try both localhost and 127.0.0.1
        try:
            res1 = s.connect_ex(('127.0.0.1', port))
            if res1 == 0: return True
            res2 = s.connect_ex(('localhost', port))
            if res2 == 0: return True
        except Exception:
            pass
        return False

def is_greenmail_responding(imap_port, retries=1, delay=0.5):
    """Try a quick IMAP connection to see if it's actually Greenmail, with optional retries."""
    for attempt in range(retries):
        try:
            # Use a short timeout for the connection
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                # Try 127.0.0.1
                connected = False
                try:
                    s.connect(('127.0.0.1', imap_port))
                    connected = True
                except Exception:
                    try:
                        s.connect(('localhost', imap_port))
                        connected = True
                    except Exception:
                        pass
                
                if connected:
                    # If we connected, try to see if it sends a greeting
                    res = s.recv(1024)
                    if not res:
                        logger.warning(f"Connection to Greenmail port {imap_port} succeeded, but received no data (b''). This usually means Greenmail is binding to 127.0.0.1 inside the container and is inaccessible from the host. Try adding -Dgreenmail.hostname=0.0.0.0 to your docker run command.")
                    if b"OK IMAP4rev1" in res:
                        return True
        except Exception:
            pass
        
        if attempt < retries - 1:
            time.sleep(delay)
            
    return False

@pytest.fixture(scope="session")
def mail_server():
    """
    Check if Greenmail server is running.
    If not running, skip tests that depend on it instead of raising RuntimeError.
    Includes retries for better reliability in CI/slow environments.
    """
    smtp_port = 3025
    imap_port = 3143

    # Initial check if ports are open
    is_running = is_port_open(smtp_port) and is_port_open(imap_port)
    
    # If initial check fails, or to be sure, try with retries for integration tests
    # We use 5 retries with 1s delay (total ~5s wait) to give server time to start
    if not is_running:
        # Re-check ports with a bit more patience
        for _ in range(5):
            time.sleep(1)
            if is_port_open(smtp_port) and is_port_open(imap_port):
                is_running = True
                break
    
    if is_running:
        # Check if it's actually responding correctly as IMAP
        is_responding = is_greenmail_responding(imap_port, retries=1, delay=0.0)
        if not is_responding:
            is_running = True # Still set to True if port is open, but maybe show a small warning
        else:
            is_running = True

    return {
        "smtp_port": smtp_port,
        "imap_port": imap_port,
        "running": is_running
    }

@pytest.fixture(autouse=True)
def skip_if_no_greenmail(request, mail_server):
    """
    Automatically skip integration tests if Greenmail is not running.
    """
    if "tests/integration" in str(request.fspath) and not mail_server["running"]:
        pytest.skip("Greenmail server is not running. Skipping integration tests.")

@pytest.fixture
def mail_config(tmp_path, mail_server):
    """
    Create a temporary wugong config that points to the Greenmail server.
    """
    # If mail_server is not running and we're not in integration test, 
    # we can still provide a config, but init_mailbox will fail.
    # So we only call init_mailbox if it's running.
    
    config_dir = tmp_path / ".wugong"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    db_path = config_dir / "emails.db"
    
    master_password = "test_password"
    salt_bytes = b"test_salt_123456" # 16 bytes
    salt_b64 = base64.b64encode(salt_bytes).decode()
    
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
    login_method = "Password"
    auth_method = "Password"
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
    login_method = "Password"
    auth_method = "Password"
    [accounts.auth]
    username = "user2"
    password = "{encrypted_pw2}"
"""
    with open(config_path, "w") as f:
        f.write(content)
    
    if mail_server.get("running"):
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
def cleanup_mailboxes(request, mail_server):
    """
    Automatically clear mailboxes after each test (only for integration tests).
    """
    # Only run for integration tests
    if "tests/integration" not in str(request.fspath):
        yield
        return

    yield
    if not mail_server.get("running"):
        return

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
