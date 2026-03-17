# Wugong Email CLI User Guide

This document provides a detailed overview of all available commands, parameters, and usage examples for the Wugong Email CLI tool.

## Global Options

These options can be used **before or after** any subcommand.

### Flexible Interaction
Wugong Email's wizards (`init`, `account add`, `configure`) support **partial interaction**:
- If you provide a parameter via the command line (e.g., `--friendly-name "MyQQ"`), the wizard will **skip** that question.
- If you don't provide a parameter, the wizard will ask you interactively.
- This is perfect for combining the ease of a GUI-like wizard with the speed of a CLI.

| Option | Shorthand | Description |
| :--- | :--- | :--- |
| `--version` | `-v` | Show the version of Wugong Email. |
| `--encryption-password` | `-p` | Specify the encryption password (can also be set via `WUGONG_PASSWORD` environment variable). |
| `--log-level` | `-L` | Override the console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). |
| `--non-interactive` | | Run in non-interactive mode. |
| `--json` | | Output result in a single, standardized JSON block. |

---

## 1. Initialization and Configuration

### `init`
Initialize Wugong Email, set encryption options, and configure background sync schedules.
- **Usage**: `wugong init`
- **Parameters**:
    - `--encrypt-creds`: Enable credential encryption.
    - `--no-encrypt-creds`: Disable credential encryption.
    - `--encrypt-emails`: Encrypt locally cached emails.
    - `--no-encrypt-emails`: Disable email encryption.
    - `--console-log-level`: Set console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    - `--file-log-level`: Set file log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    - `--sync-interval`: Sync interval in minutes (0 to disable).
    - `--non-interactive`: Run in non-interactive mode.
- **Note**: This must be run before using the tool for the first time.

### `configure`
Modify existing sync settings, intervals, or log levels.
- **Usage**: `wugong configure`
- **Parameters**:
    - `--console-log-level`: Set console log level.
    - `--file-log-level`: Set file log level.
    - `--sync-interval`: Sync interval in minutes.
    - `--non-interactive`: Run in non-interactive mode.

---

## 2. Account Management (`account`)

Manage your connected email accounts.

### `account list`
List all configured accounts.
- **Usage**: `wugong account list`
- **Parameters**:
    - `--verbose`, `-v`: Show detailed account statistics (total/unseen) and server settings.

### `account add`
Add a new email account (interactive wizard or non-interactive).
- **Usage**: `wugong account add [options]`
- **Parameters**:
    - `--friendly-name`, `-n`: Friendly name for the account.
    - `--provider`: Email provider (`gmail`, `outlook`, `qq`, `163`, `other`).
    - `--login-method`: Login method (`Account/Password`, `OAuth2`).
    - `--username`, `-u`: Email address.
    - `--password`, `-P`: Email password or OAuth2 refresh token.
    - `--imap-server`: IMAP server address.
    - `--imap-port`: IMAP server port.
    - `--imap-tls`: IMAP TLS method (`SSL/TLS`, `STARTTLS`, `Plain`).
    - `--smtp-server`: SMTP server address.
    - `--smtp-port`: SMTP server port.
    - `--smtp-tls`: SMTP TLS method (`SSL/TLS`, `STARTTLS`, `Plain`).
    - `--client-id`: OAuth2 Client ID.
    - `--client-secret`: OAuth2 Client Secret.
    - `--auth-url`: OAuth2 Authorization URL.
    - `--token-url`: OAuth2 Token URL.
    - `--scopes`: OAuth2 Scopes (comma separated).
    - `--redirect-uri`: OAuth2 Redirect URI.
    - `--sync-limit`: Number of emails to download initially (e.g., 20, 50 or 'all').
    - `--non-interactive`: Run in non-interactive mode.
- **Example**:
    - `wugong account add` (interactive wizard)
    - `wugong account add -n "My Gmail" --provider gmail -u user@gmail.com -P "app-password" --non-interactive`

### `account delete`
Delete a specific email account.
- **Usage**: `wugong account delete -a <account_name>`
- **Parameters**:
    - `--account`, `-a`: **(Required)** Friendly name of the account to delete.
- **Example**: `wugong account delete -a my_gmail`

---

## 3. Email Browsing and Synchronization

### `list`
List emails from local cache or the remote server.
- **Parameters**:
    - `--account`, `-a`: Specify the account name; uses the "default" account (the first configured) if omitted. Use `all` to list emails from all configured accounts.
    - `--limit`, `-l`: Limit the number of emails displayed.
    - `--all`: List all available emails.
    - `--verbose`, `-v`: Show more details (folder name and sender email address).
    - `--keyword`, `-k`: Search for keywords in the subject or body.
    - `--from-user`, `-f`: Filter by sender email or name.
    - `--since`: Search emails since a specific date (e.g., `01-Jan-2024`).
    - `--before`: Search emails before a specific date (e.g., `31-Dec-2024`).
    - `--local`: Query only from the local cache; do not connect to the remote IMAP server.
    - `--folder`: Specify the folder (default: `INBOX`).
    - `--sort`: Sort field (`date`, `subject`, `from`), default is `date`.
    - `--order`: Sort order (`asc`, `desc`), default is `desc`.
- **Examples**:
    - `wugong list` (Show latest emails for the default account)
    - `wugong list -a my_gmail --limit 20`
    - `wugong list -a all` (Show emails from all configured accounts)
    - `wugong list --keyword "invoice" --local`

### `sync`
Sync latest emails from the server to the local cache.
- **Parameters**:
    - `--account`, `-a`: Specify the account name or use `all`. If omitted, defaults to `all`.
    - `--limit`, `-l`: Limit the number of emails to fetch.
    - `--all`: Sync all available emails (overrides limit).
    - `--folder`: Specify the folder to sync (default: `INBOX`).
- **Examples**:
    - `wugong sync` (Sync all accounts)
    - `wugong sync -a my_gmail --folder "Sent"`
    - `wugong sync -a my_gmail --all` (Perform a full sync for a specific account)

---

## 4. Email Operations

### `read`
Read and display the content of a specific email.
- **Parameters**:
    - `--id`, `-i`: **(Required)** Email UID.
    - `--account`, `-a`: Specify the account.
    - `--folder`: Specify the folder (default: `INBOX`).
    - `--text`: Extract and show plain text content (strips HTML tags).
    - `--raw`: Show raw email content.
    - `--browser`: Open the email's HTML content in the default web browser.
- **Examples**:
    - `wugong read -i 123`
    - `wugong read -i 123 --text`
    - `wugong read -i 456 -a my_gmail --browser`

### `send`
Send an email.
- **Parameters**:
    - `--to`, `-t`: **(Required)** Recipient email address.
    - `--subject`, `-s`: **(Required)** Email subject.
    - `--body`, `-b`: Email body. If omitted, an editor or interactive input will be opened.
    - `--account`, `-a`: Specify the sending account.
    - `--attach`: File paths for attachments (supports multiple).
- **Examples**:
    - `wugong send -t user@example.com -s "Hello" -b "This is a test"`
    - `wugong send -t boss@work.com -s "Report" --attach ./report.pdf ./data.csv`

### `delete`
Delete a specific email.
- **Parameters**:
    - `--id`, `-i`: **(Required)** Email UID.
    - `--account`, `-a`: Specify the account.
    - `--folder`: Specify the folder (default: `INBOX`).
- **Examples**:
    - `wugong delete -i 123`

---

## 5. Folder Management (`folder`)

### `folder list`
List all folders for a specific account.
- **Parameters**:
    - `--account`, `-a`: Specify the account name; uses the default account if omitted.
- **Example**: `wugong folder list`

### `folder create`
Create a new folder on the remote server.
- **Parameters**:
    - `name`: **(Required)** Positional argument. Name of the folder to create.
    - `--account`, `-a`: Specify the account name; uses the default account if omitted.
- **Example**: `wugong folder create "My Work"`

### `folder delete`
Delete a folder from the remote server.
- **Parameters**:
    - `name`: **(Required)** Positional argument. Name of the folder to delete.
    - `--account`, `-a`: Specify the account name; uses the default account if omitted.
- **Example**: `wugong folder delete "Old Trash"`

### `folder move`
Move an email from one folder to another.
- **Parameters**:
    - `id`: **(Required)** Email UID.
    - `dest`: **(Required)** Destination folder name.
    - `--account`, `-a`: Specify the account name; uses the default account if omitted.
    - `--src`: Source folder (default: `INBOX`).
- **Example**: `wugong folder move 123 "Archive"`

---

## 6. System Maintenance

### `upgrade`
Check and update Wugong Email to the latest version.
- **Usage**: `wugong upgrade [options]`
- **Parameters**:
    - `--force`, `-f`: Force upgrade even if up-to-date.
    - `--non-interactive`: Run in non-interactive mode.
- **Example**: `wugong upgrade --force`

### `uninstall`
Uninstall Wugong Email and its related configurations.
- **Usage**: `wugong uninstall [options]`
- **Parameters**:
    - `--keep-data`: Keep local email cache and database.
    - `--non-interactive`: Run in non-interactive mode.
- **Example**: `wugong uninstall --keep-data --non-interactive`
