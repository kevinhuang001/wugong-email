import argparse
import sys
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from mail import MailManager
import config

logger = logging.getLogger("cli.sync")
console = Console()

def handle_sync(args: argparse.Namespace, manager: MailManager) -> None:
    target_accounts = manager.accounts if args.account == "all" or not args.account else (
        [acc] if (acc := manager.get_account_by_name(args.account)) else []
    )

    if not target_accounts:
        if args.account:
            console.print(f"[red]Error: Account '{args.account}' not found.[/red]")
        else:
            console.print("[yellow]No accounts configured yet. Run 'wugong account add' to get started.[/yellow]")
        return

    try:
        prompt_text = "Enter encryption password for all accounts:" if len(target_accounts) > 1 else f"Enter encryption password for '{target_accounts[0].get('friendly_name', 'default')}':"
        password = config.get_verified_password(manager.config, args, prompt_text)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    folder = getattr(args, "folder", "INBOX") or "INBOX"

    for account in target_accounts:
        account_name = account.get("friendly_name") or "default"
        sync_limit = -1 if args.all else (args.limit if args.limit is not None else 0)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
            disable=not sys.stdin.isatty()
        ) as progress:
            sync_task = progress.add_task(f"[green]Syncing {account_name} ({folder})...", total=None)
            
            def update_progress(current, total, description=None):
                progress.update(sync_task, total=total, completed=current, description=f"[green]Syncing {account_name} ({folder}): {description or ''}")

            emails, metadata = manager.syncer.sync_emails(
                account, password, 
                limit=sync_limit, 
                progress_callback=update_progress,
                folder=folder
            )

        if metadata.get("is_offline", False):
            console.print(f"[red]❌ Sync failed for {account_name} ({folder}): {metadata.get('error') or 'Connection failed'}.[/red]")
        else:
            console.print(f"[green]✅ {account_name}: Sync complete ({len(metadata.get('new_emails', []))} new emails fetched from {folder}).[/green]")
        console.print("-" * (console.width or 80))
