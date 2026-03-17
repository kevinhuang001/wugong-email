# Changelog

All notable changes to this project will be documented in this file.

## [1.1.2] - 2026-03-17

### Features
- **Enhanced OAuth2 UX**: Added a prominent Rich-based panel to display the OAuth2 authorization URL in the console. This ensures usability in headless environments (e.g., SSH) where a browser cannot be automatically opened.

## [1.1.1] - 2026-03-16

### Features
- **Improved Upgrade UX**: `wugong upgrade` now uses `rich.console` for real-time status updates, preventing silent termination during update checks.
- **Enhanced Version Comparison**: Added semantic version parsing that correctly handles 'v' prefixes and ensures "already up to date" prompts are shown when local version >= remote version.
- **Enhanced Test Coverage**: Added new unit tests for version parsing and message rendering logic.

### Fixed
- **Fixed Unit Test Failures**: Resolved multiple failures in `test_read.py` and `test_maintain.py` by correctly mocking TTY environments and aligning error-handling assertions.

## [1.1.0] - 2026-03-16

### Features
- **Clean Wizard UI**: Redesigned interactive wizard styles to remove bold text and heavy background highlighting from recommended options. 
    - Recommended options are now identified solely by a pointer (»), ensuring a cleaner and more professional look.
    - Removed "(Recommended)" text from encryption prompts, relying on default selection and pointer instead.
- **Enhanced JSON Interactivity**: Refactored the `read` command to support interactive display mode selection even when the `--json` flag is used, provided the command is run in a TTY.
- **Global Questionary Styling**: Standardized the appearance of all interactive prompts across the entire CLI (account setup, configuration, mail reading, folder management, etc.) using a unified custom style in `CLIRenderer`.

### Fixed
- **JSON Output Consistency**: Ensured that the `read` command correctly outputs a single JSON block regardless of whether an interactive selection was made.
- **Style Inheritance**: Fixed an issue where `questionary`'s default theme (like purple background) would persist on highlighted items by explicitly disabling reverse video and inheriting terminal backgrounds.

## [1.0.9] - 2026-03-16

### Features
- **JSON Output Standardization**: All CLI commands now produce a single, valid JSON block when the `--json` flag is used, facilitating easier parsing for AI agents and automated scripts.
- **Result Aggregation**: Multi-account operations (such as `sync all`, `list all`, and `account list`) now aggregate results from all target accounts into a single JSON object or array.
- **Unified Error Handling in JSON**: Errors encountered during multi-account operations are collected and returned within the final JSON block, providing a comprehensive status report.
- **Improved Account Wizard**: The `account add` wizard now collects and reports all interactive status messages in a single JSON response when running in JSON mode.
- **Integrated Maintenance CLI**: Merged `upgrade` and `uninstall` logic directly into the `maintain.py` module. All maintenance tasks are now handled natively via the Python CLI (`wugong upgrade` and `wugong uninstall`), eliminating the need for external shell scripts.
- **Strict uv Dependency Management**: Standardized on `uv` as the mandatory dependency manager across all platforms.
    - Updated `install.ps1` and `install.sh` to require `uv` and removed the legacy `pip` fallback.
    - Refactored `maintain.py` upgrade logic to strictly use system-level `uv`.
- **Enhanced Encrypted Search and Sorting**: Implemented Python-side sorting and filtering for encrypted fields in `MailStorageManager` to ensure correct results when local cache encryption is enabled.
- **Improved Upgrade UX**: Added a confirmation step before upgrading and implemented rich Markdown rendering for remote changelogs to show "What's new" during the upgrade process.
- **Git Availability Check**: Added proactive checks for `git` availability before attempting source-based upgrades.
- **Dependency Update Automation**: Integrated automatic dependency updates (using `uv` or `pip`) into the upgrade flow to ensure the environment is always up-to-date.

### Fixed
- **IMAP UID Command Syntax**: Added parentheses around `\\Seen` flag in `reader.py` to comply with RFC 3501.
- **Test Infrastructure Enhancements**: 
    - Standardized all integration tests to verify JSON output consistency.
    - Resolved multiple unit test failures in `test_account.py`, `test_sync.py`, and `test_list.py` by aligning assertions with new patterns.
    - Updated `conftest.py` to include `user2` in the default test environment and improved JSON extraction.
    - Resolved naming conflicts in `test_workflow.py` by using unique account names.
- **AttributeError in Tests**: Resolved a critical issue where `CLIRenderer` was returning JSON strings instead of dictionaries.
- **ID Type Mismatches**: Fixed comparison failures in `test_delete.py` and `test_read.py` by adopting string-based ID comparisons.
- **Send Parameter Fix**: Corrected recipient handling in `test_send.py` to use friendly names.
- **Upgrade Failure Fix**: Resolved an issue where the `upgrade` command would incorrectly attempt `python -m uv`.
- **JSON Output Cleanliness**: Eliminated redundant or malformed JSON blocks across all CLI commands.
- **Code Cleanup**: Removed all legacy `.sh` and `.ps1` upgrade/uninstall scripts.
- **Command Routing**: Fixed CLI command routing in `main.py` to correctly pass arguments and the mail manager to maintenance handlers.
- **Dependency Synchronization**: Synchronized `requirements.txt` with missing `requests` and `werkzeug` libraries.

## [1.0.8] - 2026-03-15

### Features
- **Verbose List Mode**: Added `--verbose` flag to `account list` and `list` commands. In `account list`, it shows server-side statistics (total and unseen messages) and connection details. In `list`, it reveals additional columns like folder names and sender email addresses.
- **Global Account Summary**: `account list` now includes a summary footer displaying the total number of cached and unseen emails across all configured accounts.
- **Enhanced Rendering**: Updated `CLIRenderer` to support dynamic column visibility and optional headers in email tables.

### Fixed
- **Dependency Management**: Synchronized `requirements.txt` with the actual project usage. Added missing `requests` and `werkzeug` libraries to ensure stable installation.
- **Import Audit**: Conducted a full codebase audit of import statements to verify all third-party dependencies are correctly listed.

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
