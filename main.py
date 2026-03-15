import argparse
import sys
import os
import socket
from pathlib import Path

from mail import MailManager
from cli.commands import (
    handle_list, 
    handle_read, 
    handle_delete, 
    handle_send, 
    handle_sync, 
    handle_account,
    handle_folder
)
from cli.configure import handle_init, handle_configure
from cli.maintain import handle_upgrade, handle_uninstall
from logger import setup_logger, update_console_level

from rich.console import Console

# Set global timeout for all network operations
socket.setdefaulttimeout(30)

# Pre-initialize logger with defaults
logger = setup_logger("cli")
console = Console()

def main() -> None:
    # Common arguments for all commands
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--encryption-password", "-p", default=argparse.SUPPRESS, help="Encryption password (also looks for WUGONG_PASSWORD environment variable)")
    common_parser.add_argument("--log-level", "-L", default=argparse.SUPPRESS, help="Override console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    common_parser.add_argument("--non-interactive", action="store_true", default=argparse.SUPPRESS, help="Run in non-interactive mode")
    
    parser = argparse.ArgumentParser(description="Wugong Email CLI Manager", parents=[common_parser])
    parser.add_argument("--version", "-v", action="store_true", help="Show the version of Wugong Email")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", parents=[common_parser], help="List accounts or emails")
    list_parser.add_argument("account", nargs="?", help="Friendly name of the account to list emails from (use 'all' for all accounts)")
    list_parser.add_argument("--limit", "-l", type=int, help="Number of emails to list per account (default from config)")
    list_parser.add_argument("--all", action="store_true", help="List all available emails")
    list_parser.add_argument("--keyword", "-k", help="Search by keyword in subject or body")
    list_parser.add_argument("--from-user", "-f", help="Search by sender's email or name")
    list_parser.add_argument("--since", help="Search emails since date (e.g., 01-Jan-2024)")
    list_parser.add_argument("--before", help="Search emails before date (e.g., 31-Dec-2024)")
    list_parser.add_argument("--local", action="store_true", help="Only query from local cache, do not use IMAP")
    list_parser.add_argument("--folder", help="Specific folder to list (default: INBOX)")
    list_parser.add_argument("--sort", choices=["date", "subject", "from"], default="date", help="Sort by field")
    list_parser.add_argument("--order", choices=["asc", "desc"], default="desc", help="Sort order")

    # Read command
    read_parser = subparsers.add_parser("read", parents=[common_parser], help="Read a specific email")
    read_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    read_parser.add_argument("--id", "-i", required=True, help="Email ID to read")
    read_parser.add_argument("--folder", help="Specific folder (default: INBOX)")
    read_parser.add_argument("--text", action="store_true", help="Extract text from HTML content")
    read_parser.add_argument("--raw", action="store_true", help="Show raw email content (no extraction)")
    read_parser.add_argument("--browser", action="store_true", help="Open email in default web browser")

    # Delete command
    delete_parser = subparsers.add_parser("delete", parents=[common_parser], help="Delete a specific email")
    delete_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    delete_parser.add_argument("--id", "-i", required=True, help="Email ID to delete")
    delete_parser.add_argument("--folder", help="Specific folder (default: INBOX)")

    # Send command
    send_parser = subparsers.add_parser("send", parents=[common_parser], help="Send an email")
    send_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    send_parser.add_argument("--to", "-t", required=True, help="Recipient email address")
    send_parser.add_argument("--subject", "-s", required=True, help="Email subject")
    send_parser.add_argument("--body", "-b", help="Email body (if not provided, an editor or multiline input will be opened)")
    send_parser.add_argument("--attach", nargs="+", help="Files to attach")

    # Sync command
    sync_parser = subparsers.add_parser("sync", parents=[common_parser], help="Sync latest emails from server")
    sync_parser.add_argument("account", nargs="?", help="Friendly name of the account to sync (use 'all' for all accounts)")
    sync_parser.add_argument("--limit", "-l", type=int, help="Limit number of emails to fetch (default: 0 = use config/recent)")
    sync_parser.add_argument("--all", action="store_true", help="Sync all available emails (overrides limit)")
    sync_parser.add_argument("--folder", default="INBOX", help="Specific folder to sync (default: INBOX)")

    # Init command
    init_parser = subparsers.add_parser("init", parents=[common_parser], help="Setup master password & sync schedule")
    init_parser.add_argument("--encrypt-creds", action="store_true", default=None, help="Enable credential encryption")
    init_parser.add_argument("--no-encrypt-creds", action="store_false", dest="encrypt_creds", help="Disable credential encryption")
    init_parser.add_argument("--encrypt-emails", action="store_true", default=None, help="Encrypt locally cached emails")
    init_parser.add_argument("--no-encrypt-emails", action="store_false", dest="encrypt_emails", help="Disable email encryption")
    init_parser.add_argument("--console-log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Console log level")
    init_parser.add_argument("--file-log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="File log level")
    init_parser.add_argument("--sync-interval", type=int, help="Sync interval in minutes (0 to disable)")

    # Account management
    account_parser = subparsers.add_parser("account", parents=[common_parser], help="Manage email accounts")
    account_subparsers = account_parser.add_subparsers(dest="account_command", help="Account subcommands")
    account_subparsers.add_parser("list", parents=[common_parser], help="List configured accounts")
    
    acc_add_parser = account_subparsers.add_parser("add", parents=[common_parser], help="Add a new email account")
    acc_add_parser.add_argument("--friendly-name", "-n", help="Friendly name for the account")
    acc_add_parser.add_argument("--provider", choices=["gmail", "outlook", "qq", "163", "other"], help="Email provider")
    acc_add_parser.add_argument("--login-method", choices=["Account/Password", "OAuth2"], help="Login method")
    acc_add_parser.add_argument("--username", "-u", help="Email address")
    acc_add_parser.add_argument("--imap-server", help="IMAP server address")
    acc_add_parser.add_argument("--imap-port", type=int, help="IMAP server port")
    acc_add_parser.add_argument("--imap-tls", choices=["SSL/TLS", "STARTTLS", "Plain"], help="IMAP TLS method")
    acc_add_parser.add_argument("--smtp-server", help="SMTP server address")
    acc_add_parser.add_argument("--smtp-port", type=int, help="SMTP server port")
    acc_add_parser.add_argument("--smtp-tls", choices=["SSL/TLS", "STARTTLS", "Plain"], help="SMTP TLS method")
    acc_add_parser.add_argument("--password", "-P", help="Email password or OAuth2 refresh token")
    acc_add_parser.add_argument("--client-id", help="OAuth2 Client ID")
    acc_add_parser.add_argument("--client-secret", help="OAuth2 Client Secret")
    acc_add_parser.add_argument("--auth-url", help="OAuth2 Authorization URL")
    acc_add_parser.add_argument("--token-url", help="OAuth2 Token URL")
    acc_add_parser.add_argument("--scopes", help="OAuth2 Scopes (comma separated)")
    acc_add_parser.add_argument("--redirect-uri", help="OAuth2 Redirect URI")
    acc_add_parser.add_argument("--sync-limit", help="Number of emails to download initially (e.g., 20, 50 or 'all')")
    acc_del_parser = account_subparsers.add_parser("delete", parents=[common_parser], help="Delete an email account")
    acc_del_parser.add_argument("name", help="Friendly name of the account to delete")

    # Folder management
    folder_parser = subparsers.add_parser("folder", parents=[common_parser], help="Manage folders and move emails")
    folder_subparsers = folder_parser.add_subparsers(dest="folder_command", help="Folder subcommands")
    
    # List folders
    folder_list_parser = folder_subparsers.add_parser("list", parents=[common_parser], help="List folders for an account")
    folder_list_parser.add_argument("account", nargs="?", help="Account name (uses default if not specified)")
    
    # Create folder
    folder_create_parser = folder_subparsers.add_parser("create", parents=[common_parser], help="Create a new folder")
    folder_create_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    folder_create_parser.add_argument("name", help="Folder name to create")
    
    # Delete folder
    folder_delete_parser = folder_subparsers.add_parser("delete", parents=[common_parser], help="Delete a folder")
    folder_delete_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    folder_delete_parser.add_argument("name", help="Folder name to delete")
    
    # Move email
    folder_move_parser = folder_subparsers.add_parser("move", parents=[common_parser], help="Move email to a folder")
    folder_move_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    folder_move_parser.add_argument("id", help="Email UID")
    folder_move_parser.add_argument("dest", help="Destination folder")
    folder_move_parser.add_argument("--src", default="INBOX", help="Source folder (default: INBOX)")

    # Configure command
    configure_parser = subparsers.add_parser("configure", parents=[common_parser], help="Modify sync settings and intervals")
    configure_parser.add_argument("--console-log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Console log level")
    configure_parser.add_argument("--file-log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="File log level")
    configure_parser.add_argument("--sync-interval", type=int, help="Sync interval in minutes (0 to disable)")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", parents=[common_parser], help="Upgrade Wugong Email to the latest version")
    upgrade_parser.add_argument("--force", "-f", action="store_true", help="Force upgrade even if up-to-date")

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", parents=[common_parser], help="Uninstall Wugong Email")
    uninstall_parser.add_argument("--keep-data", action="store_true", help="Keep local email cache and database")

    args = parser.parse_args()

    if args.version:
        v_file = Path(__file__).parent / ".version"
        version = v_file.read_text().strip() if v_file.exists() else "Unknown"
        console.print(f"[bold blue]Wugong Email[/bold blue] [cyan]v{version}[/cyan]")
        return

    log_level = getattr(args, "log_level", None)
    if log_level:
        update_console_level(log_level)

    if not args.command:
        parser.print_help()
        return

    # Initialize manager
    manager = MailManager()

    # Route commands to handlers
    match args.command:
        case "list":
            handle_list(args, manager)
        case "read":
            handle_read(args, manager)
        case "delete":
            handle_delete(args, manager)
        case "send":
            handle_send(args, manager)
        case "sync":
            handle_sync(args, manager)
        case "account":
            handle_account(args, manager, account_parser)
        case "folder":
            handle_folder(args, manager)
        case "configure":
            handle_configure(args, manager)
        case "init":
            handle_init(args, manager)
        case "upgrade":
            handle_upgrade()
        case "uninstall":
            handle_uninstall()
        case _:
            parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        console.print(f"\n[bold red]Fatal Error:[/bold red] {e}")
        sys.exit(1)
