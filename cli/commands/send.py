import argparse
import logging
from rich.console import Console
import questionary
from mail import MailManager
import config
from cli.render import CLIRenderer

logger = logging.getLogger("cli.send")
console = Console()

def handle_send(args: argparse.Namespace, manager: MailManager) -> None:
    json_out = getattr(args, "json", False)
    if not (account := manager.get_account_by_name(args.account or "default")):
        CLIRenderer.render_message(f"Account '{args.account or 'default'}' not found.", type="error", json_output=json_out)
        return

    account_name = account.get("friendly_name", "default")
    try:
        password = config.get_verified_password(manager.config, args, f"Enter encryption password for '{account_name}':")
    except ValueError as e:
        CLIRenderer.render_message(f"Error: {e}", type="error", json_output=json_out)
        return

    if not (body := args.body) and not (body := questionary.text("Email Body (press enter for multiple lines, type 'DONE' on a new line to finish):", multiline=True).ask()):
        CLIRenderer.render_message("Email body is required.", type="error", json_output=json_out)
        return

    if json_out:
        try:
            manager.sender.send_email(
                account, 
                password, 
                to=args.to, 
                subject=args.subject, 
                body=body, 
                attachments=args.attach
            )
            CLIRenderer.render_message(f"Successfully sent email to {args.to}!", type="success", json_output=json_out)
        except Exception as e:
            CLIRenderer.render_message(f"Error: {e}", type="error", json_output=json_out)
            logger.error(f"Failed to send email: {e}")
    else:
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
                CLIRenderer.render_message(f"Successfully sent email to {args.to}!", type="success", json_output=json_out)
            except Exception as e:
                CLIRenderer.render_message(f"Error: {e}", type="error", json_output=json_out)
                logger.error(f"Failed to send email: {e}")
