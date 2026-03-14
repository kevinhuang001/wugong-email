# Changelog

All notable changes to this project will be documented in this file.

## [1.0.4] - 2026-03-14

### Features
- **Comprehensive Documentation**: Greatly expanded the Quick Start section in `README.md` to cover all 12 core CLI commands with detailed usage examples.
- **Improved Installation Experience**: Updated `install.sh` and `install.ps1` to display the full command list after installation, helping users get started faster.
- **CLI Visibility**: All commands available in `--help` are now fully documented in the main README and installation guides.

## [1.0.3] - 2026-03-14

### Features
- **Global Localization**: Completed full English translation of all documentation (`README.md`, `CLI_REFERENCE.md`) and source code comments, making the project accessible to a wider audience.
- **CLI Usability**: Optimized CLI parameter design by converting positional account arguments into optional flags (`--account`/`-a`) for folder-related commands, ensuring better parsing consistency.
- **Developer Experience**: Added a comprehensive `DEVELOPER.md` guide and decoupled integration tests from local system paths to support easier contributions and CI/CD integration.
- **Enhanced Documentation**: Created a detailed `CLI_REFERENCE.md` with exhaustive parameter descriptions and usage examples.

### Fixed
- **Test Portability**: Resolved hardcoded system paths in integration tests, replacing them with flexible environment variable configurations.

## [1.0.2] - 2026-03-14

### Features
- **Security & Automation**: Centralized password retrieval logic in `config.py` and added support for `--password` CLI argument and `WUGONG_PASSWORD` environment variable to enable non-interactive automation (e.g., cron jobs).
- **TLS Configuration**: Added explicit selection of TLS methods (SSL/TLS, STARTTLS, Plain) and custom ports during account setup in `wizard.py`, improving compatibility with various email providers.
- **Reading Experience**: Added `--text` and `--html` parameters to the `read` command to allow manual content type selection and avoid interactive prompts in non-TTY environments.
- **Test Suite Restructuring**: Reorganized the `tests` directory into `unit` and `integration` subfolders. Added comprehensive boundary condition tests for hybrid sync and expanded integration tests to cover all CLI parameters.

### Fixed
- **Email Sending Robustness**: Fixed SMTP sending failures for QQ, Gmail, and Outlook accounts by refining address formatting, adding EHLO handshakes before STARTTLS, and using `docmd()` for robust OAuth2 authentication.
- **Bug Fixes**: Resolved sync pending actions retry logic and fixed OAuth2 authentication string formatting in the account setup wizard.

## [1.0.1] - 2026-03-13

### Fixed
- **IMAP Search Robustness**: Improved search logic with automatic fallback: ASCII -> UTF-8 -> Local cache, ensuring compatibility with servers that don't support UTF-8 search (like some Outlook/Exchange instances).
- **Network Error Handling**: Optimized fallback logic to only trigger on `socket.timeout`, ensuring protocol and authentication errors are correctly reported to the user.
- **UI Enhancements**: Added clear `[Online]` vs `[Local]` status indicators in the email list table header, with specific warnings when UTF-8 search is unsupported by the server.
- **Bug Fixes**: Resolved `UnboundLocalError` when IMAP search failed and fixed potential encoding issues with non-ASCII search keywords.

## [1.0.0] - 2026-03-13

### Features
- **Native AI Support**: Minimalist CLI design with structured output, optimized for autonomous AI agents like OpenClaw.
- **Automated OAuth2**: Supports automatic authorization and silent background refresh for major providers including Gmail and Outlook.
- **End-to-End Encrypted Storage**: Uses PBKDF2 + Fernet to encrypt configuration files, ensuring multi-account security.
- **Multi-Account Management**: Supports unlimited accounts with built-in presets for major providers and a "default account" for quick access.
- **High-Performance Sync**: Incremental synchronization based on IMAP UIDs, supporting full metadata sync and on-demand body fetching.
- **Cross-Platform Support**: One-click installation scripts for macOS, Linux, and Windows with automatic environment configuration.
- **Smart Search & Filtering**: Supports multi-criteria filtering by keywords, sender, and date ranges.
- **Background Automation**: One-click setup for Cron (Unix) or Scheduled Tasks (Windows) to enable automatic background synchronization.
