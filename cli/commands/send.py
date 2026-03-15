import argparse
import logging
from rich.console import Console
import questionary
from mail import MailManager
import config

logger = logging.getLogger("cli.send")
console = Console()

def handle_send(args: argparse.Namespace, manager: MailManager) -> None:
    if not (account := manager.get_account_by_name(args.account or "default")):
        console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
        return

    account_name = account.get("friendly_name", "default")
    try:
        password = config.get_verified_password(manager.config, args, f"Enter encryption password for '{account_name}':")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    if not (body := args.body) and not (body := questionary.text("Email Body (press enter for multiple lines, type 'DONE' on a new line to finish):", multiline=True).ask()):
        return

    with console.status(f"[bold green]Sending email via {account_name}...") as status:
        try:
            manager.sender.send_email(
                account, 
                password, 
                to=args.to, 
                subject=args.subject, 
                body=body, 
                attachments=args.attach
            )
            console.print(f"[green]Successfully sent email to {args.to}![/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            logger.error(f"Failed to send email: {e}")
