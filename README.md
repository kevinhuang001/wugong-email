# Wugong Email 🚀

A minimalist, secure, TUI-based command-line email manager. Supports multi-account management, OAuth2 automation, end-to-end encrypted storage, and powerful search capabilities.

## ✨ Features

- **Minimalist TUI**: Beautiful terminal interface powered by `Rich` and `Questionary`.
- **Progressive Sync**: Real-time progress bars for email synchronization and metadata fetching.
- **Offline-First Deletion**: Delete emails instantly with background synchronization and offline queuing.
- **Multi-Account Support**: Pre-configured for major providers like Gmail, Outlook, QQ, 163, with support for a "default account".
- **Security First**: End-to-end encryption for configuration files using PBKDF2 + Fernet.
- **OAuth2 Automation**: Built-in local server for automatic Access/Refresh Token exchange and silent background refresh.
- **Smart Search**: Multi-criteria filtering by keywords, sender, and date ranges.
- **Automatic Sync**: Cross-client deletion synchronization to keep your local cache clean.

---

## 🛠️ Installation

### 🍎 macOS / 🐧 Linux
We provide an automated installation script that handles Python version checks, dependency installation, and environment setup.

1. **Quick Remote Installation**:
   ```bash
   curl -sSL https://raw.githubusercontent.com/kevinhuang001/wugong-email/main/install.sh | bash
   ```

2. **Local Installation**:
   If you have cloned the repository, run:
   ```bash
   bash install.sh
   ```

3. **Configure Environment Path**:
   After installation, add the following line to your `~/.zshrc` or `~/.bashrc`:
   ```bash
   export PATH="$PATH:$HOME/.wugong"
   ```
   Then apply the changes: `source ~/.zshrc`.

---

### 🪟 Windows
1. **Quick Remote Installation (PowerShell)**:
   ```powershell
   irm https://raw.githubusercontent.com/kevinhuang001/wugong-email/main/install.ps1 | iex
   ```

2. **Local Installation**:
   If you have cloned the repository, open PowerShell and run:
   ```powershell
   .\install.ps1
   ```

3. **Configure Environment Path**:
   Add `%USERPROFILE%\.wugong` to your system's `PATH` environment variable.

---

## 🚀 Quick Start

### 0. Initialization
Run the initialization command to setup master encryption and periodic sync scheduling.
```bash
wugong init
```
*Note: This command will set up a Cron job (Linux/macOS) or Scheduled Task (Windows) for automatic background syncing.*

### 1. Configure Account
Run the configuration wizard to add your first email account.
```bash
wugong account add
```
*Tip: You can set the first account as the "default account" to skip entering the account name in future `list` commands.*

### 2. View Emails (List)
- **View default account**:
  ```bash
  wugong list
  ```
- **View specific account**:
  ```bash
  wugong list work
  ```

### 3. Sync Emails (Sync)
Wugong uses a full metadata sync strategy. This means it fetches all email headers (Subject, From, Date) but does not download the body until you read the email.
- **Sync all accounts**:
  ```bash
  wugong sync
  ```
- **Sync specific account**:
  ```bash
  wugong sync work
  ```

### 4. Read Email (Read)
After getting an email ID from the `list` or `sync` command, use the `read` command to view its content. Once read, the content is cached locally and encrypted.
- **Read email from specific account**:
  ```bash
  wugong read -a outlook -i 1234
  ```
- **Arguments**:
  - `-a, --account`: Optional. Friendly name of the account.
  - `-i, --id`: Required. Unique ID of the email on the IMAP server.

### 5. Delete Email (Delete)
Delete an email from the server and local cache. If offline, the deletion will be queued and synced when you next run `sync` or `list`.
- **Delete email from specific account**:
  ```bash
  wugong delete -a outlook -i 1234
  ```

### 6. Send Email (Send)
Send an email with optional attachments:
- **Send simple email**:
  ```bash
  wugong send -t recipient@example.com -s "Hello" -b "This is the body"
  ```
- **Send with attachments**:
  ```bash
  wugong send -t recipient@example.com -s "Files" -b "See attached" --attach file1.pdf file2.jpg
  ```

### 7. Account Management
- **List all accounts**: `wugong account list`
- **Add new account**: `wugong account add`
- **Delete account**: `wugong account delete <name>`

---

## 🔍 Search and Filtering (AND Logic)

All search parameters follow **AND** logic, meaning all conditions must be met simultaneously.

### Parameter Description
- `-k, --keyword`: Search for keywords in subject or body.
- `-f, --from-user`: Specify the sender (supports name or email address).
- `--since`: Search for emails **after** this date (Format: `DD-Mon-YYYY`, e.g., `01-Jan-2024`).
- `--before`: Search for emails **before** this date (Format: `DD-Mon-YYYY`, e.g., `31-Dec-2024`).
- `-l, --limit`: Limit the number of displayed items (default: 10).

### Usage Examples
- **Search for important emails from a specific sender**:
  ```bash
  wugong list -f "boss@company.com" -k "Report"
  ```
- **Search for all emails since the beginning of the year**:
  ```bash
  wugong list --since 01-Jan-2026
  ```
- **Advanced search (Account + Keyword + Date Range)**:
  ```bash
  wugong list outlook -k "Invoice" --since 01-Mar-2026 --before 12-Mar-2026
  ```

---

## 🛠️ Update and Uninstall

Maintenance is now integrated directly into the `wugong` command:

1. **Upgrade**:
   Checks for new commits in the remote repository and syncs changes to your installation upon confirmation. Displays current and latest version during the process.
   ```bash
   wugong upgrade
   ```

2. **Uninstall**:
   Removes the installation directory `~/.wugong` and configuration directory `~/.config/wugong` (with a prompt to keep configuration).
   ```bash
   wugong uninstall
   ```

---

## 📝 Logging

Wugong Email logs its background synchronization activities to help you monitor and troubleshoot the periodic sync task.

- **Sync Log Location**: `~/.wugong/sync.log` (or `%USERPROFILE%\.wugong\sync.log` on Windows)
- **What's logged**: Success/failure status of background syncs, number of new emails found, and any errors encountered during the process.

You can view the logs in real-time using:
- **macOS/Linux**: `tail -f ~/.wugong/sync.log`
- **Windows (PowerShell)**: `Get-Content "$HOME\.wugong\sync.log" -Wait`

---

## 📁 Directory Structure
- **Executable Binaries**: `~/.wugong/` (Source code and virtual environment)
- **Configuration**: `~/.config/wugong/config.toml` (Overrideable via `WUGONG_CONFIG` environment variable)
