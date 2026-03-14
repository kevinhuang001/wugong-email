import argparse
import logging
from rich.console import Console
from rich.table import Table
from mail import MailManager
import config

logger = logging.getLogger("cli.folder")
console = Console()

def handle_folder(args: argparse.Namespace, manager: MailManager) -> None:
    if not (account := manager.get_account_by_name(args.account or "default")):
        console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
        return

    account_name = account.get("friendly_name", "default")
    password = ""
    if (manager.encryption_enabled or manager.config.get("general", {}).get("encrypt_emails", False)) and not (password := config.get_encryption_password(args, f"Enter encryption password for '{account_name}':")):
        return

    try:
        # Connect to IMAP
        mail = manager.connector.get_imap_connection(account, password)
        if not mail:
            console.print(f"[red]Error: Failed to connect to IMAP server for {account_name}.[/red]")
            return

        try:
            match args.folder_command:
                case "list":
                    folders = manager.folder_manager.list_folders(mail)
                    table = Table(title=f"Folders for {account_name}")
                    table.add_column("Folder Name", style="cyan")
                    for folder in folders:
                        table.add_row(folder)
                    console.print(table)

                case "create":
                    if not args.name:
                        console.print("[red]Error: Folder name is required.[/red]")
                        return
                    if manager.folder_manager.create_folder(mail, args.name):
                        console.print(f"[green]Successfully created folder '{args.name}'.[/green]")
                    else:
                        console.print(f"[red]Failed to create folder '{args.name}'.[/red]")

                case "delete":
                    if not args.name:
                        console.print("[red]Error: Folder name is required.[/red]")
                        return
                    import questionary
                    if questionary.confirm(f"Are you sure you want to delete folder '{args.name}'?").ask():
                        if manager.folder_manager.delete_folder(mail, args.name):
                            console.print(f"[green]Successfully deleted folder '{args.name}'.[/green]")
                        else:
                            console.print(f"[red]Failed to delete folder '{args.name}'.[/red]")

                case "move":
                    if not args.id or not args.dest:
                        console.print("[red]Error: ID and destination folder are required.[/red]")
                        return
                    source = getattr(args, "src", "INBOX") or "INBOX"
                    uids = args.id.split(",")
                    if manager.folder_manager.move_emails(mail, uids, source, args.dest):
                        console.print(f"[green]Successfully moved {len(uids)} emails from '{source}' to '{args.dest}'.[/green]")
                    else:
                        console.print(f"[red]Failed to move emails.[/red]")
                case _:
                    console.print("[yellow]Unknown folder command.[/yellow]")
        finally:
            try:
                mail.logout()
            except:
                pass
    except Exception as e:
        logger.error(f"Error handling folder command: {e}")
        console.print(f"[red]Error: {e}[/red]")
