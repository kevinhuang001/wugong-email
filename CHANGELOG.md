# Changelog

All notable changes to this project will be documented in this file.

## [1.1.6] - 2026-03-13

### Fixed
- **Stability Improvement**: Fixed a `NoneType` error in `wugong list` command where `subject`, `from`, or `from_email` fields being null would cause a crash. Added robust `None` checks and fallback to empty strings.

## [1.1.5] - 2026-03-13

### Added
- **Unified Wrapper Script**: Extracted `wugong` (Bash) and `wugong.bat` (Windows) into separate, standalone files for better maintainability and consistent behavior across installation and updates.
- **Improved Installation Logic**: Simplified `install.sh` and `update.sh` by removing dynamic script generation, ensuring the CLI wrapper always points to the correct virtual environment and configuration paths.

### Changed
- **Aligned Update Process**: Synchronized configuration variables and environment setup between `install.sh` and `update.sh` to prevent command-not-found errors after updates.
- **Enhanced Windows Support**: Updated `install.ps1` to use the pre-defined `wugong.bat` wrapper, ensuring consistent environment variable handling on Windows.

## [1.1.0] - 2026-03-13

### Added
- **Modular Architecture**: Refactored `MailManager` into specialized modules: `auth`, `storage`, `sender`, and `manager` for better maintainability.
- **Local Email Cache**: Introduced SQLite-based caching for faster email listing and offline support.
- **Offline Mode**: View previously synced emails even without an internet connection.
- **Incremental Sync**: Only fetch new emails from the server using IMAP UIDs, significantly reducing network usage.
- **Local Fuzzy Search**: Fast, local keyword and sender filtering on cached emails.
- **Email Encryption Option**: Users can now choose to encrypt locally stored emails for enhanced privacy during the configuration wizard.
- **Sync Metadata**: The `list` command now displays the "Last Sync" time and online/offline status.

### Fixed
- Fixed an issue where reading an email could sometimes fail due to incorrect IMAP search/fetch logic (switched to UID-based fetching).

## [1.0.2] - 2026-03-13

### Fixed
- Improved HTML text extraction to correctly filter out `<style>` and `<script>` tag content, ensuring cleaner plain-text output.

## [1.0.1] - 2026-03-13

### Fixed
- Fixed issue where reading an email didn't correctly update the "Read" status on the server.
- Fixed potential logic inconsistencies where emails might be marked as read when they weren't, or vice-versa.

## [1.0.0] - 2026-03-13

### Added
- **Minimalist TUI**: Beautiful terminal interface powered by `Rich` and `Questionary`.
- **Multi-Account Support**: Pre-configured for major providers (Gmail, Outlook, QQ, 163) with support for a "default account".
- **Security First**: End-to-end encryption for configuration files using PBKDF2 + Fernet.
- **OAuth2 Automation**: Built-in local server for automatic Access/Refresh Token exchange and silent background refresh.
- **Smart Search**: Multi-criteria filtering by keywords, sender, and date ranges.
- **Integrated Maintenance**: Built-in `update` and `uninstall` commands directly within the CLI.
- **Cross-Platform Compatibility**: Native support for macOS/Linux (`.sh`) and Windows (`.ps1`).
- **HTML Content Handling**: Automatic text extraction and raw code viewing options for emails containing only HTML.
