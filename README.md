<p align="center">
  <img src="wugong.png" alt="Wugong Email Logo" width="200">
</p>

# Wugong Email

Wugong Email is a **minimalist, efficient, and AI-friendly** command-line email manager designed for the AI era. It is optimized for autonomous AI agents (like OpenClaw), making email handling as simple as executing CLI commands.

## ✨ Key Features

- **Automated OAuth2 Support**: Built-in local server for automatic Token exchange and silent background refresh for major providers like Gmail and Outlook.
- **Minimalist End-to-End Encryption**: Uses PBKDF2 + Fernet to encrypt configuration files, ensuring your account data is stored securely with a single master password.
- **Seamless Multi-Account Management**: Manage unlimited email accounts with pre-configured settings for Gmail, Outlook, QQ, 163, and more.
- **AI-Native Design**: Clean CLI output and simple configuration logic, making it easy for AI agents to read, search, and process emails.

---

## 🛠️ Installation

### 🍎 macOS / 🐧 Linux
```bash
curl -sSL https://raw.githubusercontent.com/kevinhuang001/wugong-email/main/install.sh | bash
```

### 🪟 Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/kevinhuang001/wugong-email/main/install.ps1 | iex
```

*After installation, add `~/.wugong` (Unix) or `%USERPROFILE%\.wugong` (Windows) to your PATH environment variable.*

---

## 🚀 Quick Start & Usage

For a complete list of commands and parameters, see the [CLI Reference](CLI_REFERENCE.md).

### 1. Initialization
Setup your master password and background sync schedule:
```bash
wugong init
```
*Note: Use `wugong configure` later if you need to modify sync intervals.*

### 2. Account Management

Follow the interactive wizard to add your first email account. You can provide all parameters at once, or provide some and let the wizard ask for the rest:

```bash
wugong account add          # Full interactive setup wizard
wugong account add --friendly-name "Work" --provider "gmail" # Partial interactive
wugong account list         # List all configured accounts
wugong account delete <name> # Remove an account
```

---

### 💡 Flexible Interactive Mode

Wugong Email's wizards (`init`, `account add`, `configure`) support **partial interaction**:
- If you provide a parameter via the command line (e.g., `--friendly-name "MyQQ"`), the wizard will **skip** that question.
- If you don't provide a parameter, the wizard will ask you interactively.
- This is perfect for combining the ease of a GUI-like wizard with the speed of a CLI.

---

### 3. Sync Emails
Synchronize your local cache with the IMAP server:
```bash
wugong sync                 # Sync all accounts (latest emails)
wugong sync work --limit 50 # Sync latest 50 emails for 'work' account
wugong sync --folder "Sent" # Sync a specific folder
```

### 4. List and Search Emails
Display emails from your local cache or fetch them directly from the server:
```bash
wugong list                       # Show latest emails (default account)
wugong list work --limit 20       # Show 20 emails from 'work' account
wugong list --keyword "invoice"   # Search subject/body for keywords
wugong list --verbose             # Show more details (folder, sender email)
wugong list --local               # Offline mode (cache only)
```

### 5. Read, Send, and Delete Emails
```bash
# Read an email (use -i for UID)
wugong read -i <ID>               # Read in terminal
wugong read -i <ID> --text        # Strip HTML, show plain text
wugong read -i <ID> --browser     # Open in default web browser

# Send an email
wugong send --to recipient@example.com --subject "Hello" --body "Message body"
wugong send -t user@test.com -s "File" --attach document.pdf

# Delete an email
wugong delete -i <ID>             # Delete from local and server
```

### 6. Folder Management
```bash
wugong folder list                # List all folders for default account
wugong folder create "Archive"    # Create a new folder
wugong folder move <ID> "Archive" # Move an email to a folder
```

### 7. Maintenance
```bash
wugong upgrade                    # Update to the latest version
wugong uninstall                  # Remove Wugong Email and its data
```

---

## 💡 Why Wugong Email?

In the age of AI-assisted development, you don't need a bloated GUI client. You need a secure, reliable email tool that is easy for both humans and AI to understand and interact with. Wugong Email strips away the noise and provides the core functionality you need for an efficient AI-driven workflow.
