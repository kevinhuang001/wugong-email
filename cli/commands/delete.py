import argparse
import logging
from logger import console, setup_logger
import questionary
from mail import MailManager
import config
from cli.render import CLIRenderer

logger = setup_logger("cli.delete")

def handle_delete(args: argparse.Namespace, manager: MailManager) -> None:
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
    
    folder = getattr(args, "folder", "INBOX") or "INBOX"

    if not manager.non_interactive and not questionary.confirm(f"Are you sure you want to delete email {args.id} from {account_name} ({folder})?", style=CLIRenderer.get_questionary_style()).ask():
        CLIRenderer.render_message("Deletion cancelled.", type="warning", json_output=json_out)
        return

    if json_out:
        try:
            success, message = manager.deleter.delete_email(account, password, args.id, folder=folder)
            CLIRenderer.render_message(message, type="success" if success else "warning", json_output=json_out)
        except Exception as e:
            CLIRenderer.render_message(f"Error: {e}", type="error", json_output=json_out)
    else:
        with console.status(f"[bold red]Deleting email {args.id} from {account_name} ({folder})...") as status:
            try:
                success, message = manager.deleter.delete_email(account, password, args.id, folder=folder)
                CLIRenderer.render_message(message, type="success" if success else "warning", json_output=json_out)
            except Exception as e:
                CLIRenderer.render_message(f"Error: {e}", type="error", json_output=json_out)
