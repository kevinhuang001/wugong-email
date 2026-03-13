# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-13

### Added
- Integrated `update` and `uninstall` commands directly into `wugong` CLI.
- Added native Windows support with `update.ps1` and `uninstall.ps1`.
- Implemented a more efficient file synchronization logic (no longer depends on `rsync`).
- Added HTML-to-text extraction for reading emails that only contain HTML content.
- Support for default accounts in `read` and `list` commands.

### Changed
- Simplified the `update` process to hide verbose git output.
- Optimized version checking using a local `.version` file to avoid redundant updates.
- Improved the layout of the email list for better readability.
- Translated interactive prompts to English.

### Fixed
- Fixed `UnboundLocalError` in CLI by reorganizing imports.
- Fixed a bug where reading an email would mark it as read on the server (now uses `BODY.PEEK`).
- Fixed issues with the self-update logic in `update.sh`.
