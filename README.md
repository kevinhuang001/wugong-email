# Wugong Email 🚀

A minimalist, secure, TUI-based command-line email manager. Supports multi-account management, OAuth2 automation, end-to-end encrypted storage, and powerful search capabilities.

## ✨ Features

- **Minimalist TUI**: Beautiful terminal interface powered by `Rich` and `Questionary`.
- **Multi-Account Support**: Pre-configured for major providers like Gmail, Outlook, QQ, 163, with support for a "default account".
- **Security First**: End-to-end encryption for configuration files using PBKDF2 + Fernet.
- **OAuth2 Automation**: Built-in local server for automatic Access/Refresh Token exchange and silent background refresh.
- **Smart Search**: Multi-criteria filtering by keywords, sender, and date ranges.

---

## 🛠️ Installation

We provide an automated installation script that handles Python version checks, dependency installation, and environment setup.

1. **Run Installation**:
   ```bash
   bash install.sh
   ```
2. **Configure Environment Path**:
   After installation, add the following line to your `~/.zshrc` or `~/.bashrc`:
   ```bash
   export PATH="$PATH:$HOME/.wugong"
   ```
   Then apply the changes: `source ~/.zshrc`.

---

## 🚀 Quick Start

### 1. Configure Account (Wizard)
Run the configuration wizard to add your first email account.
```bash
wugong-wizard
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

### 3. Read Email (Read)
After getting an email ID from the `list` command, use the `read` command to view its content:
- **Read email from specific account**:
  ```bash
  wugong read -a outlook -i 1234
  ```
- **Arguments**:
  - `-a, --account`: Required. Friendly name of the account.
  - `-i, --id`: Required. Unique ID of the email on the IMAP server.

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

Utility scripts are provided in the installation directory for maintenance:

1. **Update**:
   Run `./update.sh` in the source repository. It checks for new commits in the remote repository and syncs changes to your installation upon confirmation.
   ```bash
   ./update.sh
   ```

2. **Uninstall**:
   Run `./uninstall.sh` to remove the installation directory `~/.wugong` and configuration directory `~/.config/wugong`.
   ```bash
   ./uninstall.sh
   ```

---

## � Directory Structure
- **Executable Binaries**: `~/.wugong/` (Source code and virtual environment)
- **Configuration**: `~/.config/wugong/config.toml` (Overrideable via `WUGONG_CONFIG` environment variable)
