# Changelog

All notable changes to this project will be documented in this file.

## [1.0.7] - 2026-03-15

### Features
- **Strict Non-Interactive Mode**: Enforced a single-account limit in non-interactive mode to prevent accidental bulk account additions without proper verification.
- **Immediate Connection Testing**: The `account add` wizard now performs a connection test immediately after credentials are provided ("Fill one, Test one").
- **Batch Operations**: Refactored account management to support batch saving of verified accounts and sequential batch initial syncing, reducing configuration file writes and improving efficiency.
- **Enhanced UI/UX**: Replaced all standard `print` statements with `rich.console.print`, introducing color-coded status messages (Success, Error, Warning, Info) and a more modern CLI aesthetic.
- **Connection Retry Logic**: Added an interactive retry loop for failed connection tests during account setup, allowing users to correct credentials without restarting the wizard.

### Fixed
- **Error Handling**: Non-interactive connection test failures now correctly raise a `ValueError` instead of silently returning an empty list, ensuring better CI/CD integration.
- **Credential Privacy**: Removed redundant plain-text printing of connection status in favor of secure `console.status` indicators.

## [1.0.6] - 2026-03-15

### Features
- **Flexible Interactive Mode**: Enhanced `account add` wizard to skip questions for parameters already provided via CLI arguments. This allows for "partial interaction" where you can pre-fill some fields and let the wizard ask for the rest.
- **Improved Documentation**: Updated `README.md` and `CLI_REFERENCE.md` to highlight the new flexible interaction capabilities in wizards.

### Fixed
- **Sync Status Reporting**: Fixed a bug in `account add` where the initial sync would report success even if it failed (e.g., due to login errors). It now correctly displays failure messages with the specific error from the IMAP server.

## [1.0.5] - 2026-03-15

### Features
- **Unified Global Parameters**: Integrated `--encryption-password`, `--log-level`, and `--non-interactive` into a common parser, allowing them to be placed either before or after subcommands for improved CLI flexibility.
- **Enhanced Automation**: Implemented `argparse.SUPPRESS` for shared arguments to ensure global flags are not overridden by subcommand defaults, ensuring stable non-interactive behavior.
- **Code Modularization**: Refactored the monolithic `wizard.py` into specialized modules: `oauth2.py`, `configure.py`, `account.py`, and `schedule.py` for better maintainability.
- **Simplified Provider Names**: Streamlined email provider selection to use short identifiers: `qq`, `163`, `gmail`, `outlook`, and `other`.

### Fixed
- **Subcommand Recognition**: Fixed an issue where `--non-interactive` and `--encryption-password` were not recognized when placed after subcommands (e.g., `wugong list --non-interactive`).
- **Redundant Prompts**: Fixed password prompts appearing even when a valid password was provided via CLI or environment variables.
- **Encryption Fix**: Resolved "name 'encrypt_data' is not defined" error during account setup by correctly handling base64 salt decoding.
- **Validation**: Added mandatory input validation for non-interactive mode to prevent silent failures.

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
