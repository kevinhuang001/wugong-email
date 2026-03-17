import argparse
import sys
import logging
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from mail import MailManager
from cli.render import CLIRenderer
import config
from logger import console, setup_logger

logger = setup_logger("cli.sync")

def handle_sync(args: argparse.Namespace, manager: MailManager) -> None:
    json_out = getattr(args, "json", False)
    target_accounts = manager.accounts if args.account == "all" or not args.account else (
        [acc] if (acc := manager.get_account_by_name(args.account)) else []
    )

    if not target_accounts:
        if args.account:
            CLIRenderer.render_message(f"Account '{args.account}' not found.", type="error", json_output=json_out)
        else:
            CLIRenderer.render_message("No accounts configured yet. Run 'wugong account add' to get started.", type="warning", json_output=json_out)
        return

    # Only fetch password if needed:
    # 1. We are encrypting credentials (to decrypt IMAP password for remote connection)
    # 2. We are encrypting emails (to encrypt new emails before saving to cache)
    needs_password = manager.encryption_enabled or manager.encrypt_emails
    
    password = ""
    if needs_password:
        try:
            prompt_text = "Enter encryption password for all accounts:" if len(target_accounts) > 1 else f"Enter encryption password for '{target_accounts[0].get('friendly_name', 'default')}':"
            password = config.get_verified_password(manager.config, args, prompt_text, non_interactive=manager.non_interactive)
        except ValueError as e:
            CLIRenderer.render_message(f"Error: {e}", type="error", json_output=json_out)
            return
    
    folder = getattr(args, "folder", "INBOX") or "INBOX"

    all_emails = []
    errors = []
    from mail.storage_manager import Email
    for account in target_accounts:
        account_name = account.get("friendly_name") or "default"
        # If limit is not provided, default to 0 which triggers incremental sync (since last sync)
        sync_limit = -1 if args.all else (args.limit if args.limit is not None else 0)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
            disable=not sys.stdin.isatty() or json_out,
            refresh_per_second=10  # Reduce UI thread overhead
        ) as progress:
            sync_task = progress.add_task(f"[green]Syncing {account_name} ({folder})...", total=None)

            def update_progress(current, total, description=None):
                progress.update(sync_task, total=total, completed=current, description=f"[green]Syncing {account_name} ({folder}): {description or ''}")

            try:
                emails, metadata = manager.syncer.sync_emails(
                    account, password, 
                    limit=sync_limit, 
                    progress_callback=update_progress,
                    folder=folder
                )
            except Exception as e:
                logger.error(f"Error syncing {account_name}: {e}")
                if json_out:
                    errors.append({"account": account_name, "error": str(e)})
                else:
                    CLIRenderer.render_message(f"Error syncing {account_name}: {e}", type="error", json_output=json_out)
                continue

        if json_out:
            if metadata.get("is_offline", False):
                errors.append({"account": account_name, "error": metadata.get('error') or 'Connection failed', "offline": True})
            
            if emails:
                for em in emails:
                    if isinstance(em, Email):
                        em_dict = em.to_dict()
                        em_dict["account"] = account_name
                        all_emails.append(em_dict)
                    elif isinstance(em, dict):
                        em["account"] = account_name
                        all_emails.append(em)

        if not json_out:
            if metadata.get("is_offline", False):
                CLIRenderer.render_message(f"Sync failed for {account_name} ({folder}): {metadata.get('error') or 'Connection failed'}.", type="error", json_output=json_out)
            else:
                new_emails = metadata.get('new_emails', [])
                num_new = len(new_emails)
                
                # Add a newline before the result message to ensure it doesn't overlap with previous output
                console.print()
                CLIRenderer.render_message(f"{account_name}: Sync complete ({num_new} new emails fetched from {folder}).", type="success")
                if num_new > 0:
                    title = f"New Emails for [bold cyan]{account_name}[/bold cyan]"
                    if folder != "INBOX":
                        title += f" in folder [bold yellow]{folder}[/bold yellow]"
                    CLIRenderer.render_header(title)
                    CLIRenderer.render_email_table(new_emails, show_folder=True)

    if json_out:
        if errors and not all_emails:
            CLIRenderer.render_message(f"Errors occurred for {len(errors)} accounts during sync.", type="error", data={"errors": errors}, json_output=json_out)
        else:
            data = {"errors": errors} if errors else None
            CLIRenderer.render_email_table(all_emails, show_folder=True, json_output=json_out, data=data)
