# Changelog

All notable changes to this project will be documented in this file.

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
