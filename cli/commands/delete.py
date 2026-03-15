import argparse
import logging
from rich.console import Console
import questionary
from mail import MailManager
import config

logger = logging.getLogger("cli.delete")
console = Console()

def handle_delete(args: argparse.Namespace, manager: MailManager) -> None:
    if not (account := manager.get_account_by_name(args.account or "default")):
        console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
        return

    account_name = account.get("friendly_name", "default")
    try:
        password = config.get_verified_password(manager.config, args, f"Enter encryption password for '{account_name}':")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    folder = getattr(args, "folder", "INBOX") or "INBOX"

    if not getattr(args, "non_interactive", False) and not questionary.confirm(f"Are you sure you want to delete email {args.id} from {account_name} ({folder})?").ask():
        return

    with console.status(f"[bold red]Deleting email {args.id} from {account_name} ({folder})...") as status:
        try:
            success, message = manager.deleter.delete_email(account, password, args.id, folder=folder)
            status_mark = "✅" if success else "⚠️"
            color = "green" if success else "yellow"
            console.print(f"[{color}]{status_mark} {message}[/{color}]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
