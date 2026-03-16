# Developer Guide

This document provides information for developers who want to contribute to Wugong Email, set up a development environment, and run tests.

## 🛠️ Development Environment Setup

### 1. Prerequisites
- Python 3.8 or higher.
- `uv` (recommended for faster dependency management) or `pip`.

### 2. Installation
Clone the repository and install dependencies:

```bash
# Clone the repository
git clone https://github.com/kevinhuang001/wugong-email.git
cd wugong-email

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 3. Project Structure
- `cli/`: Command-line interface logic and command definitions.
- `mail/`: Core email handling logic (IMAP/SMTP, storage, encryption).
- `tests/`: Test suite, divided into `unit` and `integration` tests.
- `main.py`: Entry point for the CLI.
- `configure.py`: Interactive setup wizard for configuration and initial setup.
- `account.py`: Account management logic and account add wizard.
- `oauth2.py`: OAuth2 authentication flow handling.
- `schedule.py`: Periodic sync scheduling (Cron/Task Scheduler).

---

## 🧪 Testing

Wugong Email uses `pytest` for testing. The tests are categorized into unit and integration tests.

### 1. Running All Tests
To run all tests (excluding those that require real account credentials):
```bash
pytest -m "not real_account"
```

### 2. Unit Tests
Unit tests focus on individual components and use mocks for external dependencies.
```bash
pytest tests/unit
```
All unit tests for CLI commands now include scenarios for both standard output and `--json` output.

### 3. Integration Tests
Integration tests are divided into two categories:

#### Greenmail Server Tests (Recommended)
These tests use a Greenmail Docker container to simulate IMAP/SMTP servers. This provides a more robust and feature-complete testing environment than local mocks.

**Prerequisites:**
- Docker Desktop must be installed and running.

**Steps to run:**
1. Start the Greenmail container with pre-configured users (required by tests):
   ```bash
   docker run -it --rm \
     -e GREENMAIL_OPTS="-Dgreenmail.setup.test.all -Dgreenmail.users=user1:password,user2:password" \
     -p 3025:3025 -p 3143:3143 \
     greenmail/standalone:2.0.0
   ```
2. Run the tests:
   ```bash
   # Ensure PYTHONPATH is set to the current directory
   export PYTHONPATH=$PYTHONPATH:.
   pytest tests/integration/
   ```

**What these tests do:**
- Automatically detect the Greenmail server on ports 3025 (SMTP) and 3143 (IMAP).
- Initialize the mailboxes with rich test data (folders like `Archive`, `Personal`, `Shopping`, etc., and multiple seeded emails) before each test run.
- Mimic user CLI workflows (e.g., `account add`, `sync`, `list`, `read`, `send`, `delete`, `folder`).
- Verify both standard and JSON outputs for all commands.
- Standardize JSON output by extracting the first valid JSON block from the output.
- Automatically clear the mailboxes after each test to ensure isolation.

#### Real Account Tests (Optional)
These tests interact with real email servers and require a valid configuration. By default, they are skipped if no configuration is found.

To run these tests, you need to provide a test configuration directory containing a `config.toml` (and optionally `cache.db`).

**Steps to configure real account tests:**
1. Create a directory (e.g., `test_env/`) and place a valid `config.toml` in it.
2. Set the following environment variables:
   - `WUGONG_TEST_CONFIG_DIR`: Path to the directory containing your test `config.toml`.
   - `WUGONG_PASSWORD`: The master password used to encrypt the configuration.

```bash
export WUGONG_TEST_CONFIG_DIR=$(pwd)/test_env
export WUGONG_PASSWORD="your_master_password"
pytest tests/integration/real_account
```

---

## 🔒 Security and Encryption

- Configuration files (`config.toml`) are encrypted using **Fernet** (symmetric encryption) with a key derived from the master password using **PBKDF2**.
- Sensitive information like OAuth2 tokens and app passwords are never stored in plain text.
- For testing purposes, you can use a fixed `WUGONG_PASSWORD` in your environment to avoid interactive prompts.

## 📝 Code Style and Contributions
- Follow PEP 8 guidelines.
- Ensure all new features have corresponding unit and/or integration tests.
- Use meaningful commit messages and document any major architectural changes.
- **Important**: All documentation and code comments should be in **English**.
