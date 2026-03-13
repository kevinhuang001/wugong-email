# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1] - 2026-03-13

### Fixed
- Fixed issue where reading an email didn't correctly update the "Read" status on the server.
- Fixed potential logic inconsistencies where emails might be marked as read when they weren't, or vice-versa.

## [1.0.0] - 2026-03-13

### Added
- Integrated `update` and `uninstall` commands directly into `wugong` CLI.
- Added native Windows support with `update.ps1` and `uninstall.ps1`.
- Implemented a more efficient file synchronization logic (no longer depends on `rsync`).
- Added HTML-to-text extraction for reading emails that only contain HTML content.
- Support for default accounts in `read` and `list` commands.
- Security First: End-to-end encryption for configuration files using PBKDF2 + Fernet.
- OAuth2 Automation: Built-in local server for automatic Access/Refresh Token exchange.
- Smart Search: Multi-criteria filtering by keywords, sender, and date ranges.

### Changed
- Simplified the `update` process to hide verbose git output.
- Optimized version checking using a local `.version` file to avoid redundant updates.
- Improved the layout of the email list for better readability.
- Translated interactive prompts to English.

### Fixed
- Fixed `UnboundLocalError` in CLI by reorganizing imports.
- Fixed self-update syntax errors in shell scripts.
