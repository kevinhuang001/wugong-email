# Changelog

All notable changes to this project will be documented in this file.

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
