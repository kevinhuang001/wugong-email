import argparse
import sys
import logging
from typing import Any, cast
from logger import console, setup_logger
from mail import MailManager
from cli.render import CLIRenderer
import config

logger = setup_logger("cli.list")

def handle_list(args: argparse.Namespace, manager: MailManager) -> None:
    json_out = getattr(args, "json", False)
    if not manager.accounts:
        CLIRenderer.render_message("No accounts configured yet. Run 'wugong account add' to get started.", type="warning", json_output=json_out)
        return

    if not args.account:
        # Default to "default" account if no specific account is provided
        target_account_name = "default"
    else:
        target_account_name = args.account

    target_accounts = manager.accounts if target_account_name == "all" else [
        acc for acc in [manager.get_account_by_name(target_account_name)] if acc
    ]
    
    if not target_accounts:
        if not args.account:
            CLIRenderer.render_message("No accounts configured yet. Run 'wugong account add' to get started.", type="warning", json_output=json_out)
        else:
            CLIRenderer.render_message(f"Account '{target_account_name}' not found.", type="error", json_output=json_out)
        return

    # Only fetch password if needed:
    # 1. We are encrypting emails (must decrypt local cache to show)
    # 2. We are going online AND credentials encryption is enabled (to decrypt IMAP password)
    is_local = getattr(args, "local", False)
    needs_password = manager.encrypt_emails or (not is_local and manager.encryption_enabled)
    
    password = ""
    if needs_password:
        try:
            prompt = "Enter encryption password for all accounts:" if target_account_name == "all" else f"Enter encryption password for '{target_accounts[0]['friendly_name']}':"
            password = config.get_verified_password(manager.config, args, prompt, non_interactive=manager.non_interactive)
        except ValueError as e:
            CLIRenderer.render_message(f"Error: {e}", type="error", json_output=json_out)
            return
    
    all_emails = []
    errors = []
    from mail.storage_manager import Email
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
            if sys.stdin.isatty() and not is_local and not json_out:
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

            if json_out:
                if emails:
                    for em in emails:
                        if isinstance(em, Email):
                            em_dict = em.to_dict()
                            em_dict["account"] = account_name
                            all_emails.append(em_dict)
                        elif isinstance(em, dict):
                            em["account"] = account_name
                            all_emails.append(em)
                continue

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
            
            CLIRenderer.render_header(title, " | ".join(filters), json_output=json_out)
            CLIRenderer.render_email_table(emails or [], show_folder=(folder == "all"), verbose=getattr(args, "verbose", False), json_output=json_out)
        except Exception as e:
            logger.error(f"Error listing {account_name}: {e}")
            if json_out:
                errors.append({"account": account_name, "error": str(e)})
            else:
                CLIRenderer.render_message(f"Error listing {account_name}: {e}", type="error", json_output=json_out)

    if json_out:
        if errors and not all_emails:
            CLIRenderer.render_message(f"Errors occurred for {len(errors)} accounts.", type="error", data={"errors": errors}, json_output=json_out)
        else:
            folder = getattr(args, "folder", "all") or "all"
            data = {"errors": errors} if errors else None
            CLIRenderer.render_email_table(all_emails, show_folder=(folder == "all"), verbose=getattr(args, "verbose", False), json_output=json_out, data=data)
