import argparse
import logging
import questionary
from logger import console, setup_logger
from rich.table import Table
from mail import MailManager
import config
from cli.render import CLIRenderer

logger = setup_logger("cli.folder")

def handle_folder(args: argparse.Namespace, manager: MailManager) -> None:
    json_out = getattr(args, "json", False)
    if not (account := manager.get_account_by_name(args.account or "default")):
        CLIRenderer.render_message(f"Account '{args.account or 'default'}' not found.", type="error", json_output=json_out)
        return

    account_name = account.get("friendly_name", "default")
    
    # Only fetch password if needed for decrypting credentials
    needs_password = manager.encryption_enabled
    
    password = ""
    if needs_password:
        try:
            password = config.get_verified_password(manager.config, args, f"Enter encryption password for '{account_name}':", non_interactive=manager.non_interactive)
        except ValueError as e:
            CLIRenderer.render_message(f"Error: {e}", type="error", json_output=json_out)
            return
    
    try:
        # Connect to IMAP
        mail = manager.connector.get_imap_connection(account, password)
        if not mail:
            CLIRenderer.render_message(f"Failed to connect to IMAP server for {account_name}.", type="error", json_output=json_out)
            return

        try:
            match args.folder_command:
                case "list":
                    folders = manager.folder_manager.list_folders(mail)
                    folders_data = []
                    
                    verbose = getattr(args, "verbose", False)
                    if verbose:
                        if json_out:
                            for folder in folders:
                                status = manager.folder_manager.get_folder_status(mail, folder)
                                cached_count = manager.storage_manager.get_email_count(account_name, folder)
                                cached_unseen = manager.storage_manager.get_email_count(account_name, folder, only_unseen=True)
                                
                                folders_data.append({
                                    "name": folder,
                                    "cached_count": cached_count,
                                    "cached_unseen": cached_unseen,
                                    "server_total": status["messages"],
                                    "server_unseen": status["unseen"]
                                })
                        else:
                            with console.status(f"[bold green]Fetching folder stats for {account_name}..."):
                                for folder in folders:
                                    status = manager.folder_manager.get_folder_status(mail, folder)
                                    cached_count = manager.storage_manager.get_email_count(account_name, folder)
                                    cached_unseen = manager.storage_manager.get_email_count(account_name, folder, only_unseen=True)
                                    
                                    folders_data.append({
                                        "name": folder,
                                        "cached_count": cached_count,
                                        "cached_unseen": cached_unseen,
                                        "server_total": status["messages"],
                                        "server_unseen": status["unseen"]
                                    })
                    else:
                        for folder in folders:
                            cached_count = manager.storage_manager.get_email_count(account_name, folder)
                            cached_unseen = manager.storage_manager.get_email_count(account_name, folder, only_unseen=True)
                            folders_data.append({
                                "name": folder,
                                "cached_count": cached_count,
                                "cached_unseen": cached_unseen
                            })
                    
                    CLIRenderer.render_folders_table(folders_data, account_name, verbose=verbose, json_output=json_out)

                case "create":
                    if not args.name:
                        CLIRenderer.render_message("Folder name is required.", type="error", json_output=json_out)
                        return
                    if manager.folder_manager.create_folder(mail, args.name):
                        CLIRenderer.render_message(f"Successfully created folder '{args.name}'.", type="success", json_output=json_out)
                    else:
                        CLIRenderer.render_message(f"Failed to create folder '{args.name}'.", type="error", json_output=json_out)

                case "delete":
                    if not args.name:
                        CLIRenderer.render_message("Folder name is required.", type="error", json_output=json_out)
                        return
                    
                    if manager.non_interactive:
                         if manager.folder_manager.delete_folder(mail, args.name):
                            CLIRenderer.render_message(f"Successfully deleted folder '{args.name}'.", type="success", json_output=json_out)
                         else:
                            CLIRenderer.render_message(f"Failed to delete folder '{args.name}'.", type="error", json_output=json_out)
                    elif questionary.confirm(f"Are you sure you want to delete folder '{args.name}'?", style=CLIRenderer.get_questionary_style()).ask():
                        if manager.folder_manager.delete_folder(mail, args.name):
                            CLIRenderer.render_message(f"Successfully deleted folder '{args.name}'.", type="success", json_output=json_out)
                        else:
                            CLIRenderer.render_message(f"Failed to delete folder '{args.name}'.", type="error", json_output=json_out)
                    else:
                        CLIRenderer.render_message("Deletion cancelled.", type="warning", json_output=json_out)

                case "move":
                    if not args.id or not args.dest:
                        CLIRenderer.render_message("ID and destination folder are required.", type="error", json_output=json_out)
                        return
                    source = getattr(args, "src", "INBOX") or "INBOX"
                    uids = args.id.split(",")
                    if manager.folder_manager.move_emails(mail, uids, source, args.dest):
                        CLIRenderer.render_message(f"Successfully moved {len(uids)} emails from '{source}' to '{args.dest}'.", type="success", json_output=json_out)
                    else:
                        CLIRenderer.render_message("Failed to move emails.", type="error", json_output=json_out)
                case _:
                    CLIRenderer.render_message("Unknown folder command.", type="warning", json_output=json_out)
        finally:
            try:
                mail.logout()
            except:
                pass
    except Exception as e:
        logger.error(f"Error handling folder command: {e}")
        CLIRenderer.render_message(f"Error: {e}", type="error", json_output=json_out)
