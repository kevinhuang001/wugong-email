# Wugong Email 🚀

Wugong Email is a **minimalist, efficient, and AI-friendly** command-line email manager designed for the AI era. It is optimized for developers and AI agents (like Cursor or Trae), making email handling as simple as writing code.

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

### 1. Initialization
Setup your master password and background sync schedule:
```bash
wugong init
```

### 2. Add an Account
Follow the interactive wizard to add your first email account:
```bash
wugong account add
```

### 3. List Emails
Display the latest emails from your default or specific account:
```bash
wugong list                       # Show default account
wugong list work --limit 20       # Show 20 emails from 'work' account
wugong list --keyword "invoice"   # Search by keyword
wugong list --from "boss"         # Filter by sender
wugong list --since 2024-01-01    # Filter by date
```

### 4. Sync Emails
Synchronize your local cache with the IMAP server:
```bash
wugong sync                       # Sync all accounts
wugong sync work --limit 100      # Sync latest 100 emails for 'work'
```

### 5. Read an Email
Read the content of a specific email by its ID:
```bash
wugong read -i <ID>
```

### 6. Send an Email
Send a quick email from the command line:
```bash
wugong send --to recipient@example.com --subject "Hello" --body "Message body"
```

### 7. Maintenance
```bash
wugong upgrade                    # Update to the latest version
wugong uninstall                  # Remove Wugong Email
```

---

## 💡 Why Wugong Email?

In the age of AI-assisted development, you don't need a bloated GUI client. You need a secure, reliable email tool that is easy for both humans and AI to understand and interact with. Wugong Email strips away the noise and provides the core functionality you need for an efficient AI-driven workflow.
