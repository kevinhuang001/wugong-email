import argparse
import sys
import logging
from typing import Any, cast
from rich.console import Console
from mail import MailManager
from cli.render import CLIRenderer
import config

logger = logging.getLogger("cli.list")
console = Console()

def handle_list(args: argparse.Namespace, manager: MailManager) -> None:
    if not manager.accounts:
        console.print("[yellow]No accounts configured yet. Run 'wugong account add' to get started.[/yellow]")
        return

    target_accounts = manager.accounts if args.account == "all" else [
        acc for acc in [manager.get_account_by_name(args.account or "default")] if acc
    ]
    
    if not target_accounts:
        console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
        return

    try:
        prompt = "Enter encryption password for all accounts:" if args.account == "all" else f"Enter encryption password for '{target_accounts[0]['friendly_name']}':"
        password = config.get_verified_password(manager.config, args, prompt)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    for account in cast(list[dict[str, Any]], target_accounts):
        account_name = account.get("friendly_name", "default")
        
        # Folder filter
        folder = getattr(args, "folder", "all") or "all"
        
        # Sorting
        sort_by = getattr(args, "sort", "date")
        order = getattr(args, "order", "desc")
        
        search_criteria = {
            "keyword": args.keyword,
            "from": args.from_user,
            "since": args.since,
            "before": args.before,
            "folder": folder if folder != "all" else None
        }
        
        list_limit = -1 if args.all else (args.limit if args.limit is not None else 10)
        is_local = getattr(args, "local", False)
        
        logger.info(f"Listing emails for {account_name} (limit={list_limit}, local={is_local}, folder={folder})")
        
        status_msg = f"[bold green]Fetching cached emails for {account_name}..." if is_local else f"[bold green]Querying {account_name}..."
        
        try:
            if sys.stdin.isatty() and not is_local:
                with console.status(status_msg):
                    emails, metadata = manager.lister.query_emails(
                        account, password, 
                        limit=list_limit, 
                        search_criteria=search_criteria, 
                        local_only=is_local,
                        sort_by=sort_by,
                        order=order
                    )
            else:
                emails, metadata = manager.lister.query_emails(
                    account, password, 
                    limit=list_limit, 
                    search_criteria=search_criteria, 
                    local_only=is_local,
                    sort_by=sort_by,
                    order=order
                )

            status_tag = "[bold red]Fallback to Local[/bold red]" if metadata.get("is_fallback") else ("[yellow]Local[/yellow]" if metadata.get("is_offline") else "[green]Online[/green]")
            title = f"Emails for [bold cyan]{account_name}[/bold cyan] ({status_tag})"
            if folder != "all":
                title += f" in folder [bold yellow]{folder}[/bold yellow]"
            
            if metadata.get("is_fallback") and "UTF-8 not supported" in str(metadata.get("error", "")):
                title += " [bold red](UTF-8 not supported by mail server)[/bold red]"
            
            filters = []
            if any(v for k, v in search_criteria.items() if k != "folder"):
                active_filters = [f"[dim]{k}[/dim]=[bold]{v}[/bold]" for k, v in search_criteria.items() if v and k != "folder"]
                filters.append(f"[dim]Filters:[/dim] {', '.join(active_filters)}")
            
            filters.append(f"[dim]Sort:[/dim] [bold]{sort_by}[/bold] ([bold]{order}[/bold])")
            
            CLIRenderer.render_header(title, " | ".join(filters))
            CLIRenderer.render_email_table(emails or [], show_folder=(folder == "all"))
        except Exception as e:
            logger.error(f"Error listing {account_name}: {e}")
            console.print(f"[red]Error listing {account_name}: {e}[/red]")
