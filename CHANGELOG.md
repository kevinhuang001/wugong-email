# Changelog

All notable changes to this project will be documented in this file.

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
