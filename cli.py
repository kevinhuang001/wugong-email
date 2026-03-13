import argparse
import sys
import os
import questionary
from datetime import datetime
from email.utils import parsedate_to_datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from mail_manager import MailManager
from wizard import run_wizard

console = Console()

def format_short_date(date_str):
    if not date_str or date_str == "N/A":
        return "N/A"
    
    try:
        dt = parsedate_to_datetime(date_str)
        now = datetime.now(dt.tzinfo)
        
        if dt.date() == now.date():
            # Today: HH:MM
            return dt.strftime("%H:%M")
        elif dt.year == now.year:
            # This year: MM-DD
            return dt.strftime("%m-%d")
        else:
            # Other years: YYYY-MM-DD
            return dt.strftime("%Y-%m-%d")
    except:
        # Fallback to a shorter version if parsing fails
        return date_str[:11] if len(date_str) > 11 else date_str

def main():
    parser = argparse.ArgumentParser(description="Wugong Email CLI Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List accounts or emails")
    list_parser.add_argument("account", nargs="?", help="Friendly name of the account to list emails from")
    list_parser.add_argument("--limit", "-l", type=int, default=10, help="Number of emails to list")
    list_parser.add_argument("--keyword", "-k", help="Search by keyword in subject or body")
    list_parser.add_argument("--from-user", "-f", help="Search by sender's email or name")
    list_parser.add_argument("--since", help="Search emails since date (e.g., 01-Jan-2024)")
    list_parser.add_argument("--before", help="Search emails before date (e.g., 31-Dec-2024)")

    # Read command
    read_parser = subparsers.add_parser("read", help="Read a specific email")
    read_parser.add_argument("--account", "-a", required=True, help="Account name")
    read_parser.add_argument("--id", "-i", required=True, help="Email ID to read")

    # Send command
    send_parser = subparsers.add_parser("send", help="Send an email")
    send_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    send_parser.add_argument("--to", "-t", required=True, help="Recipient email address")
    send_parser.add_argument("--subject", "-s", required=True, help="Email subject")
    send_parser.add_argument("--body", "-b", help="Email body content")
    send_parser.add_argument("--attach", nargs="+", help="Paths to files to attach")

    # Configure command
    subparsers.add_parser("configure", help="Run the configuration wizard")

    # Account command
    account_parser = subparsers.add_parser("account", help="Manage email accounts")
    account_subparsers = account_parser.add_subparsers(dest="account_command", help="Account operations")
    
    # account list
    account_subparsers.add_parser("list", help="List all configured accounts")
    
    # account add
    account_subparsers.add_parser("add", help="Add a new account (same as configure)")
    
    # account delete
    delete_parser = account_subparsers.add_parser("delete", help="Delete a configured account")
    delete_parser.add_argument("name", help="Friendly name of the account to delete")

    # Update command
    subparsers.add_parser("update", help="Update Wugong Email to the latest version")

    # Uninstall command
    subparsers.add_parser("uninstall", help="Uninstall Wugong Email")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = MailManager()

    if args.command == "list":
        if not args.account:
            # Check for default account
            default_acc = manager.get_account_by_name("default")
            if default_acc:
                # Use default account automatically
                account = default_acc
                args.account = "default"
                # Proceed to fetch emails below
            else:
                # List configured accounts
                table = Table(title="Configured Email Accounts")
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Friendly Name", style="magenta")
                table.add_column("Method", style="green")
                table.add_column("IMAP Server", style="yellow")

                for idx, acc in enumerate(manager.accounts, 1):
                    table.add_row(
                        str(idx),
                        acc.get("friendly_name", "N/A"),
                        acc.get("login_method", "N/A"),
                        f"{acc.get('imap_server')}:{acc.get('imap_port')}"
                    )
                console.print(table)
                console.print("\nUse `list <AccountName>` to view emails for a specific account.")
                return

        # List emails for a specific account (either specified or default)
        account = manager.get_account_by_name(args.account)
        if not account:
            console.print(f"[red]Error: Account '{args.account}' not found.[/red]")
            return

        password = ""
        if manager.encryption_enabled:
            password = questionary.password(f"Enter encryption password for '{args.account}':").ask()
            if not password:
                return

        with console.status(f"[bold green]Fetching emails for {args.account}...") as status:
            try:
                search_criteria = {
                    "keyword": args.keyword,
                    "from": args.from_user,
                    "since": args.since,
                    "before": args.before
                }
                emails = manager.fetch_emails(account, password, limit=args.limit, search_criteria=search_criteria)
                
                title = f"Latest {len(emails)} Emails for {args.account}"
                if any(search_criteria.values()):
                    active_filters = [f"{k}={v}" for k, v in search_criteria.items() if v]
                    title += f" (Filters: {', '.join(active_filters)})"

                table = Table(title=title, show_lines=False)
                table.add_column("S", justify="center", width=1) # Status column
                table.add_column("ID", style="cyan", justify="right")
                table.add_column("From", style="magenta", width=25)
                table.add_column("Subject", style="white", overflow="ellipsis")
                table.add_column("Date", style="green", no_wrap=True)

                for em in emails:
                    # Mark unread with *
                    status_mark = "" if em.get("seen") else "*"
                    
                    # Clean subject and from for single-line display
                    subject = em["subject"].replace("\n", " ").replace("\r", "")
                    from_user = em["from"].replace("\n", " ").replace("\r", "")
                    
                    table.add_row(
                        status_mark,
                        em["id"],
                        from_user,
                        subject,
                        format_short_date(em["date"])
                    )
                console.print(table)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    elif args.command == "configure":
        run_wizard()

    elif args.command == "account":
        if args.account_command == "list":
            if not manager.accounts:
                console.print("[yellow]No accounts configured yet. Run 'wugong configure' or 'wugong account add' to get started.[/yellow]")
                return
                
            table = Table(title="Configured Email Accounts")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Friendly Name", style="magenta")
            table.add_column("Method", style="green")
            table.add_column("IMAP Server", style="yellow")

            for idx, acc in enumerate(manager.accounts, 1):
                table.add_row(
                    str(idx),
                    acc.get("friendly_name", "N/A"),
                    acc.get("login_method", "N/A"),
                    f"{acc.get('imap_server')}:{acc.get('imap_port')}"
                )
            console.print(table)
            
        elif args.account_command == "add":
            run_wizard()
            
        elif args.account_command == "delete":
            account_name = args.name
            account = manager.get_account_by_name(account_name)
            if not account:
                console.print(f"[red]Error: Account '{account_name}' not found.[/red]")
                return
                
            confirm = questionary.confirm(f"Are you sure you want to delete account '{account_name}'?").ask()
            if confirm:
                # Remove from manager.accounts
                manager.accounts = [acc for acc in manager.accounts if acc.get("friendly_name") != account_name]
                # Update manager.config["accounts"]
                manager.config["accounts"] = manager.accounts
                # Save to config file
                manager._save_config()
                console.print(f"[green]Successfully deleted account '{account_name}'.[/green]")
            else:
                console.print("[yellow]Deletion cancelled.[/yellow]")
        else:
            # Show help for account command if no subcommand provided
            account_parser.print_help()

    elif args.command == "update":
        install_dir = os.path.dirname(os.path.abspath(__file__))
        update_script = os.path.join(install_dir, "update.sh")
        if os.path.exists(update_script):
            os.system(f"bash {update_script}")
        else:
            console.print(f"[red]Error: update.sh not found in {install_dir}[/red]")

    elif args.command == "uninstall":
        install_dir = os.path.dirname(os.path.abspath(__file__))
        uninstall_script = os.path.join(install_dir, "uninstall.sh")
        if os.path.exists(uninstall_script):
            os.system(f"bash {uninstall_script}")
        else:
            console.print(f"[red]Error: uninstall.sh not found in {install_dir}[/red]")

    elif args.command == "read":
        account = manager.get_account_by_name(args.account)
        if not account:
            console.print(f"[red]Error: Account '{args.account}' not found.[/red]")
            return

        password = ""
        if manager.encryption_enabled:
            password = questionary.password(f"Enter encryption password for '{args.account}':").ask()
            if not password:
                return

        with console.status(f"[bold green]Fetching content for email {args.id}...") as status:
            try:
                content = manager.get_email_content(account, password, args.id)
                if content:
                    panel = Panel(
                        content,
                        title=f"Email Content (ID: {args.id})",
                        subtitle=f"Account: {args.account}",
                        border_style="green",
                        padding=(1, 2)
                    )
                    console.print(panel)
                else:
                    console.print(f"[yellow]No text content found for email {args.id}.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    elif args.command == "send":
        account_name = args.account or "default"
        account = manager.get_account_by_name(account_name)
        if not account:
            console.print(f"[red]Error: Account '{account_name}' not found.[/red]")
            return

        password = ""
        if manager.encryption_enabled:
            password = questionary.password(f"Enter encryption password for '{account_name}':").ask()
            if not password:
                return

        body = args.body
        if not body:
            # If body is not provided, open interactive text area
            body = questionary.text("Email Body (press enter for multiple lines, type 'DONE' on a new line to finish):", multiline=True).ask()
            if body is None:
                return

        with console.status(f"[bold green]Sending email via {account_name}...") as status:
            try:
                manager.send_email(
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

if __name__ == "__main__":
    main()
