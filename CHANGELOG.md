# Changelog

All notable changes to this project will be documented in this file.

## [1.9.7] - 2026-03-13

### Added
- **Configure Command**: Added `wugong configure` to allow users to modify synchronization intervals after initialization.
- **Smart Uninstallation**: `uninstall.sh` and `uninstall.ps1` now automatically detect and remove scheduled background sync tasks from Crontab (Unix/macOS) or Task Scheduler (Windows).

### Changed
- **Installation Feedback**: Updated installation scripts and README to display the latest command set and provide a clearer quick-start guide.
- **Uninstallation Flow**: Improved the uninstallation confirmation and configuration cleanup process.

## [1.9.6] - 2026-03-13

### Added
- **Background Sync Logging**: Background synchronization tasks now redirect their output to a log file located at `~/.wugong/sync.log` (Unix/macOS) or `%USERPROFILE%\.wugong\sync.log` (Windows). This allows users to easily track the status and troubleshoot periodic syncs.
- **Log Visibility in README**: Updated the documentation to include details on the log file location and how to monitor logs in real-time across different operating systems.

## [1.9.5] - 2026-03-13

### Added
- **New `configure` Command**: Added a dedicated `configure` command to allow users to modify settings like the sync interval without re-initializing the entire system.
- **Improved Password Management Guidance**: The `configure` command now explicitly informs users that the master password cannot be changed once set, and a reinstallation is required for such changes.

### Changed
- **Strict Initialization**: Modified `wugong init` to strictly prevent re-initialization if the system is already set up. Users are now redirected to the `configure` command for common setting adjustments.
- **Sync Interval Cancellation**: Enhanced the configuration process to ensure that setting the sync interval to `0` correctly cancels all scheduled tasks across both Windows (Task Scheduler) and Unix-like (Crontab) systems.

## [1.9.4] - 2026-03-13

### Changed
- **Init Re-run Guidance**: Added informative messages when running `wugong init` on an already initialized system. It now advises users to reinstall if they need to change the master password, while allowing them to update the sync interval.
- **Improved Scheduling**: Setting the sync interval to `0` now correctly removes the scheduled task from Crontab (macOS/Linux) or Task Scheduler (Windows), effectively disabling auto-sync.

## [1.9.3] - 2026-03-13

### Changed
- **Clean Installation**: Optimized `install.sh` and `install.ps1` to suppress verbose output from `git`, `pip`, and `uv`. The installation process is now much cleaner and focuses on key status updates.

## [1.9.2] - 2026-03-13

### Changed
- **Decoupled Setup**: `wugong init` now only handles configuration and encryption setup. It no longer triggers account addition. Users are prompted to run `wugong account add` manually after initialization.

## [1.9.1] - 2026-03-13

### Changed
- **Init Wizard**: Simplified `init` command by removing the immediate account addition prompt. It now focuses purely on core configuration and provides a clear tip to use `wugong account add`.

## [1.9.0] - 2026-03-13

### Added
- **Seamless Setup**: If encryption is not configured when adding an account, the initialization wizard is now automatically triggered, and the newly set master password is reused for the current account setup.

### Changed
- **Changelog Display**: Update scripts and `upgrade` command now strictly show only the changes between the current and latest versions, filtering out older history.

## [1.8.9] - 2026-03-13

### Changed
- **Encryption Logic**: Master password is now required if *either* credential encryption or local email body encryption is enabled.
- **CLI Password Prompts**: Updated all CLI commands to prompt for the master password if email body encryption is enabled, even if credential encryption is off.

## [1.8.8] - 2026-03-13

### Changed
- **Mandatory Encryption**: `init` command now requires a master password to be set. Credential encryption is now enabled by default to ensure security.

## [1.8.7] - 2026-03-13

### Changed
- **Installation Docs**: Updated `install.sh` and `install.ps1` to display the full suite of modern commands including `init` and `sync`.

## [1.8.6] - 2026-03-13

### Changed
- **Update UX**: Removed changelog display from update scripts after successful update. Changelog is now only shown before confirmation.

## [1.8.5] - 2026-03-13

### Changed
- **Initial Sync**: Restored full metadata sync (unlimited) when adding a new account, as requested.

## [1.8.4] - 2026-03-13

### Added
- **Incremental Changelog**: Upgrade command now shows all release notes between your current version and the latest version.

### Changed
- **Default Limits**: `list` command now defaults to 10 emails for display, while `sync` defaults to 20 emails.
- **Scheduled Sync**: Background sync (Cron/Task Scheduler) now syncs only the latest 20 emails by default.
- **Initial Sync**: Sync after adding an account now defaults to 20 emails instead of a full metadata sync.

## [1.8.3] - 2026-03-13

### Fixed
- **Self-Update Stability (Take 2)**: Resolved persistent `bash` syntax errors during `wugong upgrade` by using `rm -f && cp` for self-updating scripts. This ensures the running shell maintains its file pointer to the original inode, preventing corruption when the file on disk is replaced.

## [1.8.2] - 2026-03-13

### Added
- **Enhanced Update Experience**: The `upgrade` command now fetches and displays the latest changelog using Markdown rendering *before* asking for confirmation.
- **Silent Update Flag**: Added `--yes` (Bash) and `-yes` (PowerShell) flags to update scripts to allow bypassing interactive confirmation when called from the CLI.

## [1.8.1] - 2026-03-13

### Changed
- **Internal Refactoring**: Renamed internal wizard functions for better clarity: `run_wizard` -> `account_add_wizard`, `run_init` -> `init_wizard`.
- **Improved Update Experience**: The `upgrade` command now displays the latest changelog after a successful update.

## [1.8.0] - 2026-03-13

### Added
- **Initialization Command**: Introduced `wugong init` to set up master encryption and sync schedules.
- **Cross-Platform Scheduling**: 
    - **Linux/macOS**: Automatic `crontab` integration for background syncing.
    - **Windows**: Automatic `Task Scheduler` (schtasks) integration.
- **Background Sync Optimization**: Added TTY detection to hide progress bars and skip password prompts during non-interactive background syncs.
- **Configurable Sync Interval**: Users can now set and modify the sync interval (in minutes) via `wugong init` or `config.toml`.

### Changed
- **Forced Initialization**: `account add` now requires a one-time initialization if not already performed.

## [1.7.0] - 2026-03-13

### Added
- **Email Deletion**: New `wugong delete` command to remove emails from both server and local cache.
- **Offline Deletion Queue**: Deletions made while offline are queued and automatically synced during the next `sync` or `list` operation.
- **Full Metadata Sync**: The `sync` command now performs a full, unlimited metadata sync (UIDs, headers) by default.
- **Cross-Client Sync**: Automatically detects and removes locally cached emails that were deleted on other clients.
- **Progress Bar**: Integrated `rich.progress` for real-time, single-line refresh progress bars during sync operations.

### Changed
- **Optimized List/Sync Defaults**: `wugong list` now defaults to 10 emails, while `sync` defaults to unlimited metadata sync.
- **Enhanced Read Caching**: Email content is now cached locally after the first read for instant subsequent access.

## [1.6.1] - 2026-03-13

### Fixed
- **Self-Update Stability**: Fixed a critical Bash syntax error (`unexpected EOF`) during `wugong upgrade` by wrapping the update script in a block to prevent partial execution during file replacement.

## [1.2.1] - 2026-03-13

### Added
- **Version Display**: `wugong upgrade` now shows current vs. latest version comparison.
- **UID-Based Sync**: Improved sync reliability by switching to full UID set comparison for cache invalidation.

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
