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
from cli.configurer import handle_init, handle_configure
from cli.maintainer import handle_upgrade, handle_uninstall
from logger import setup_logger, update_console_level

# Set global timeout for all network operations
socket.setdefaulttimeout(30)

# Pre-initialize logger with defaults
logger = setup_logger("cli")

def main() -> None:
    parser = argparse.ArgumentParser(description="Wugong Email CLI Manager")
    parser.add_argument("--version", "-v", action="store_true", help="Show the version of Wugong Email")
    parser.add_argument("--password", "-p", help="Encryption password (also looks for WUGONG_PASSWORD environment variable)")
    parser.add_argument("--log-level", "-L", help="Override console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List accounts or emails")
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
    read_parser = subparsers.add_parser("read", help="Read a specific email")
    read_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    read_parser.add_argument("--id", "-i", required=True, help="Email ID to read")
    read_parser.add_argument("--folder", help="Specific folder (default: INBOX)")
    read_parser.add_argument("--text", action="store_true", help="Extract text from HTML content")
    read_parser.add_argument("--raw", action="store_true", help="Show raw email content (no extraction)")
    read_parser.add_argument("--browser", action="store_true", help="Open email in default web browser")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a specific email")
    delete_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    delete_parser.add_argument("--id", "-i", required=True, help="Email ID to delete")
    delete_parser.add_argument("--folder", help="Specific folder (default: INBOX)")

    # Send command
    send_parser = subparsers.add_parser("send", help="Send an email")
    send_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    send_parser.add_argument("--to", "-t", required=True, help="Recipient email address")
    send_parser.add_argument("--subject", "-s", required=True, help="Email subject")
    send_parser.add_argument("--body", "-b", help="Email body (if not provided, an editor or multiline input will be opened)")
    send_parser.add_argument("--attach", nargs="+", help="Files to attach")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync latest emails from server")
    sync_parser.add_argument("account", nargs="?", help="Friendly name of the account to sync (use 'all' for all accounts)")
    sync_parser.add_argument("--limit", "-l", type=int, help="Limit number of emails to fetch (default: 0 = use config/recent)")
    sync_parser.add_argument("--all", action="store_true", help="Sync all available emails (overrides limit)")
    sync_parser.add_argument("--folder", default="INBOX", help="Specific folder to sync (default: INBOX)")

    # Account management
    account_parser = subparsers.add_parser("account", help="Manage email accounts")
    account_subparsers = account_parser.add_subparsers(dest="account_command", help="Account subcommands")
    account_subparsers.add_parser("list", help="List configured accounts")
    account_subparsers.add_parser("add", help="Add a new email account")
    acc_del_parser = account_subparsers.add_parser("delete", help="Delete an email account")
    acc_del_parser.add_argument("name", help="Friendly name of the account to delete")

    # Folder management
    folder_parser = subparsers.add_parser("folder", help="Manage folders and move emails")
    folder_subparsers = folder_parser.add_subparsers(dest="folder_command", help="Folder subcommands")
    
    # List folders
    folder_list_parser = folder_subparsers.add_parser("list", help="List folders for an account")
    folder_list_parser.add_argument("account", nargs="?", help="Account name (uses default if not specified)")
    
    # Create folder
    folder_create_parser = folder_subparsers.add_parser("create", help="Create a new folder")
    folder_create_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    folder_create_parser.add_argument("name", help="Folder name to create")
    
    # Delete folder
    folder_delete_parser = folder_subparsers.add_parser("delete", help="Delete a folder")
    folder_delete_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    folder_delete_parser.add_argument("name", help="Folder name to delete")
    
    # Move email
    folder_move_parser = folder_subparsers.add_parser("move", help="Move email to a folder")
    folder_move_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    folder_move_parser.add_argument("id", help="Email UID")
    folder_move_parser.add_argument("dest", help="Destination folder")
    folder_move_parser.add_argument("--src", default="INBOX", help="Source folder (default: INBOX)")

    # Configure command
    subparsers.add_parser("configure", help="Modify sync settings and intervals")
    
    # Init command
    subparsers.add_parser("init", help="Setup encryption and sync schedule")

    # Upgrade command
    subparsers.add_parser("upgrade", help="Upgrade Wugong Email to the latest version")

    # Uninstall command
    subparsers.add_parser("uninstall", help="Uninstall Wugong Email")

    args = parser.parse_args()

    if args.version:
        v_file = Path(__file__).parent / ".version"
        version = v_file.read_text().strip() if v_file.exists() else "Unknown"
        print(f"Wugong Email v{version}")
        return

    if args.log_level:
        update_console_level(args.log_level)

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
        print("\n[blue]Operation cancelled by user.[/blue]")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        print(f"\n[red]Fatal Error: {e}[/red]")
        sys.exit(1)
