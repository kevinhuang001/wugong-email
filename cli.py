import argparse
import sys
import os
import subprocess
import re
import questionary
from datetime import datetime
from email.utils import parsedate_to_datetime
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from mail import MailManager
from wizard import account_add_wizard, init_wizard, configure_wizard

console = Console()

def handle_list(args, manager):
    if not manager.accounts:
        console.print("[yellow]No accounts configured yet. Run 'wugong account add' to get started.[/yellow]")
        return

    # Handle "all" accounts
    target_accounts = []
    if args.account == "all":
        target_accounts = manager.accounts
    else:
        acc = manager.get_account_by_name(args.account) if args.account else manager.get_account_by_name("default")
        if not acc:
            console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
            return
        target_accounts = [acc]

    # Get password once if encryption is enabled (assume same password for all for simplicity in CLI)
    password = ""
    # We need a password if either credentials or emails are encrypted
    if manager.encryption_enabled or manager.config.get("general", {}).get("encrypt_emails", False):
        # Check if we are in a terminal (for background cron jobs)
        if not sys.stdin.isatty():
            # If not in a terminal, we can't ask for a password.
            # For now, we'll skip syncing if it's encrypted and no password can be provided.
            # In the future, this could use a system keyring.
            return

        if args.account == "all":
            prompt_text = "Enter encryption password for all accounts:"
        else:
            acc_name = target_accounts[0].get("friendly_name") or "default"
            prompt_text = f"Enter encryption password for '{acc_name}':"
        
        password = questionary.password(prompt_text).ask()
        if not password:
            return

    for account in target_accounts:
        account_name = account.get("friendly_name") or "default"
        
        # Determine limits and criteria
        search_criteria = {
            "keyword": args.keyword,
            "from": args.from_user,
            "since": args.since,
            "before": args.before
        }
        
        list_limit = 20
        if args.all:
            list_limit = -1
        elif args.limit is not None:
            list_limit = args.limit

        # 2. Fetch Results (Pure Query, No Sync)
        emails = []
        metadata = {}
        
        is_local = getattr(args, "local", False)
        status_msg = f"[bold green]Fetching cached emails for {account_name}..." if is_local else f"[bold green]Querying {account_name}..."
        
        with console.status(status_msg) as status:
            try:
                emails, metadata = manager.reader.query_emails(
                    account, password, 
                    limit=list_limit, 
                    search_criteria=search_criteria,
                    local_only=is_local
                )
            except Exception as e:
                console.print(f"[red]❌ Query failed for {account_name}: {e}. Showing cached emails.[/red]")
                emails, metadata = manager.reader.query_emails(
                    account, password, 
                    limit=list_limit, 
                    search_criteria=search_criteria,
                    local_only=True
                )

        # 3. Display Results
        try:
            if emails is None: emails = []
            
            title = f"Latest {len(emails)} Emails for {account_name}"
            if any(search_criteria.values()):
                active_filters = [f"{k}={v}" for k, v in search_criteria.items() if v]
                title += f" (Filters: {', '.join(active_filters)})"

            # Add sync info to title
            last_sync = metadata.get("last_sync", "Never")
            is_offline = metadata.get("is_offline", False)
            sync_error = metadata.get("error")
            
            if is_offline:
                status_str = f"[red](OFFLINE: {sync_error or 'Connection failed'})[/red]"
            elif is_local:
                status_str = "[yellow](CACHED)[/yellow]"
            else:
                status_str = "[green](ONLINE)[/green]"
            
            title += f"\n[dim]Last Sync: {last_sync} {status_str}[/dim]"

            table = Table(title=title, show_lines=False, box=None)
            table.add_column("", justify="center", width=1) # Status column
            table.add_column("ID", style="cyan", justify="right", width=6)
            table.add_column("From", style="magenta", width=20)
            table.add_column("Email", style="blue", width=25)
            table.add_column("Subject", style="white", ratio=1) # Use ratio to fill space
            table.add_column("Time", style="green", width=19)

            for em in emails:
                # Mark unread with *
                status_mark = "" if em.get("seen") else "*"
                
                # Clean subject and from for single-line display
                subject = (em.get("subject") or "").replace("\n", " ").replace("\r", "")
                from_user = (em.get("from") or "").replace("\n", " ").replace("\r", "")
                from_email = (em.get("from_email") or "").replace("\n", " ").replace("\r", "")
                
                # Format time: YYYY-MM-DD HH:MM:SS
                display_time = em["date"]
                try:
                    dt = parsedate_to_datetime(em["date"])
                    display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
                
                table.add_row(
                    status_mark,
                    em["id"],
                    from_user,
                    from_email,
                    subject,
                    display_time
                )
            console.print(table)
            console.print("-" * console.width) # Separator between accounts
        except Exception as e:
            console.print(f"[red]Error listing {account_name}: {e}[/red]")

def handle_read(args, manager):
    account = manager.get_account_by_name(args.account) if args.account else manager.get_account_by_name("default")
    if not account:
        console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
        return

    account_name = account.get("friendly_name") or "default"
    password = os.environ.get("WUGONG_PASSWORD", "")
    # We need a password if either credentials or emails are encrypted
    if not password and (manager.encryption_enabled or manager.config.get("general", {}).get("encrypt_emails", False)):
        password = questionary.password(f"Enter encryption password for '{account_name}':").ask()
        if not password:
            return

    with console.status(f"[bold green]Fetching content for email {args.id} via {account_name}...") as status:
        try:
            content = manager.reader.read_email(account, password, args.id)
            if content:
                if isinstance(content, dict) and content.get("type") == "html_only":
                    html_content = content.get("html", "")
                    status.stop()
                    choice = questionary.select(
                        "This email only contains HTML content. Please choose how to view it:",
                        choices=[
                            "Extract text (may be incomplete, sentences might run together)",
                            "View raw HTML code",
                            "Cancel"
                        ]
                    ).ask()
                    
                    if choice == "Extract text (may be incomplete, sentences might run together)":
                        # Remove <style> and <script> tags and their content
                        text = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                        # Basic HTML stripping for remaining tags
                        text = re.sub(r'<[^<]+?>', '', text)
                        # Replace multiple newlines, using raw strings to avoid SyntaxWarning
                        text = re.sub(r'\n\s*\n', '\n\n', text)
                        content = f"[Note: This content is text extracted from HTML]\n\n{text.strip()}"
                    elif choice == "View raw HTML code":
                        content = html_content
                    else:
                        return
                
                panel = Panel(
                    content,
                    title=f"Email Content (ID: {args.id})",
                    subtitle=f"Account: {account_name}",
                    border_style="green",
                    padding=(1, 2)
                )
                console.print(panel)
            else:
                console.print(f"[yellow]No content found for email {args.id}.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

def handle_delete(args, manager):
    account = manager.get_account_by_name(args.account) if args.account else manager.get_account_by_name("default")
    if not account:
        console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
        return

    account_name = account.get("friendly_name") or "default"
    password = os.environ.get("WUGONG_PASSWORD", "")
    # We need a password if either credentials or emails are encrypted
    if not password and (manager.encryption_enabled or manager.config.get("general", {}).get("encrypt_emails", False)):
        password = questionary.password(f"Enter encryption password for '{account_name}':").ask()
        if not password:
            return

    confirm = questionary.confirm(f"Are you sure you want to delete email {args.id} from {account_name}?").ask()
    if not confirm:
        return

    with console.status(f"[bold red]Deleting email {args.id} from {account_name}...") as status:
        try:
            success, message = manager.reader.delete_email(account, password, args.id)
            if success:
                console.print(f"[green]✅ {message}[/green]")
            else:
                console.print(f"[yellow]⚠️ {message}[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

def handle_send(args, manager):
    account = manager.get_account_by_name(args.account) if args.account else manager.get_account_by_name("default")
    if not account:
        console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
        return

    account_name = account.get("friendly_name") or "default"
    password = os.environ.get("WUGONG_PASSWORD", "")
    # We need a password if either credentials or emails are encrypted
    if not password and (manager.encryption_enabled or manager.config.get("general", {}).get("encrypt_emails", False)):
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

def handle_configure(args, manager):
    """Handles the 'configure' command to modify sync settings."""
    configure_wizard()

def handle_init(args, manager):
    """Handles the 'init' command to setup encryption and sync schedule."""
    # Check for administrative privileges if on Windows (recommended for schtasks)
    if os.name == 'nt':
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            console.print("[yellow]Warning: You are not running as administrator. Scheduling may fail.[/yellow]")
            console.print("[yellow]Please run the terminal as Administrator and try again if schtasks fails.[/yellow]\n")
    elif os.getuid() != 0:
        # On Unix, crontab doesn't need root, but it's good to mention if they want system-wide (though we don't do that)
        pass

    init_wizard()

def handle_account(args, manager, account_parser):
    match args.account_command:
        case "list":
            if not manager.accounts:
                console.print("[yellow]No accounts configured yet. Run 'wugong account add' to get started.[/yellow]")
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
            
        case "add":
            newly_added, password = account_add_wizard()
            # After adding accounts, auto-sync based on provided limits
            if newly_added:
                # Need encryption password if enabled and not already provided
                manager = MailManager()
                if (manager.encryption_enabled or manager.config.get("general", {}).get("encrypt_emails", False)) and not password:
                    password = questionary.password("Enter encryption password to start initial sync:").ask()
                    if not password: return

                for acc, limit in newly_added:
                    account_name = acc.get("friendly_name")
                    if limit == 0:
                        console.print(f"[yellow]ℹ️  {account_name}: Skipping initial sync as limit was set to 0.[/yellow]")
                        continue

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
                        sync_task = progress.add_task(f"[green]Initial sync for {account_name}...", total=None)
                        
                        def update_progress(current, total, description=None):
                            if total:
                                progress.update(sync_task, total=total, completed=current, description=f"[green]Initial sync for {account_name}: {description or ''}")
                            else:
                                progress.update(sync_task, description=f"[green]Initial sync for {account_name}: {description or ''}")

                        try:
                            # Use the limit specified in the wizard session
                            manager.reader.fetch_emails(acc, password, limit=limit, is_initial_sync=True, progress_callback=update_progress)
                            console.print(f"[green]✅ {account_name}: Initial sync complete (limit: {limit if limit > 0 else 'all'}).[/green]")
                        except Exception as e:
                            console.print(f"[red]❌ Error syncing {account_name}: {e}[/red]")
            
        case "delete":
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
        case _:
            # Show help for account command if no subcommand provided
            account_parser.print_help()

def handle_sync(args, manager):
    if not manager.accounts:
        console.print("[yellow]No accounts configured yet.[/yellow]")
        return

    target_accounts = []
    if args.account == "all":
        target_accounts = manager.accounts
    else:
        acc = manager.get_account_by_name(args.account) if args.account else manager.get_account_by_name("default")
        if not acc:
            console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
            return
        target_accounts = [acc]

    password = os.environ.get("WUGONG_PASSWORD", "")
    # We need a password if either credentials or emails are encrypted
    if not password and (manager.encryption_enabled or manager.config.get("general", {}).get("encrypt_emails", False)):
        if args.account == "all":
            prompt_text = "Enter encryption password for all accounts:"
        else:
            acc_name = target_accounts[0].get("friendly_name") or "default"
            prompt_text = f"Enter encryption password for '{acc_name}':"
        
        password = questionary.password(prompt_text).ask()
        if not password:
            return

    for account in target_accounts:
        account_name = account.get("friendly_name") or "default"
        is_tty = sys.stdin.isatty()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True, # Remove the progress bar after completion
            disable=not is_tty
        ) as progress:
            task = progress.add_task(f"[green]Syncing {account_name}...", total=None)
            
            def update_progress(current, total, description=None):
                if total:
                    progress.update(task, total=total, completed=current, description=f"[green]Syncing {account_name}: {description or ''}")
                else:
                    progress.update(task, description=f"[green]Syncing {account_name}: {description or ''}")

            try:
                # For sync command, limit only affects flag sync
                sync_limit = 100
                if args.all:
                    sync_limit = -1
                elif args.limit is not None:
                    sync_limit = args.limit
                
                _, metadata = manager.reader.fetch_emails(account, password, limit=sync_limit, progress_callback=update_progress)
                new_emails = metadata.get("new_emails", [])
                if new_emails:
                    console.print(f"[green]✅ {account_name}: {len(new_emails)} new emails[/green]")
                    # Display a small table for new emails
                    new_table = Table(box=None, show_header=False, padding=(0, 2))
                    new_table.add_column("From", style="magenta", width=25)
                    new_table.add_column("Subject", style="white")
                    for ne in new_emails[:5]: # Show up to 5 new emails
                        new_table.add_row(ne["from"], ne["subject"])
                    if len(new_emails) > 5:
                        new_table.add_row("...", f"and {len(new_emails)-5} more")
                    console.print(new_table)
                else:
                    console.print(f"[green]✅ {account_name}: No new emails.[/green]")
            except Exception as e:
                console.print(f"[red]❌ Error syncing {account_name}: {e}[/red]")

def handle_upgrade():
    """Handles the 'upgrade' command to update Wugong Email code."""
    import urllib.request
    import sys
    
    install_dir = os.path.expanduser("~/.wugong")
    version_file = os.path.join(install_dir, ".version")
    repo_url = "https://github.com/kevinhuang001/wugong-email.git"
    raw_url_base = "https://raw.githubusercontent.com/kevinhuang001/wugong-email/main"
    
    # Get current version
    current_version = "Unknown"
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            current_version = f.read().strip()
    
    console.print(f"[blue]🔄 Checking for updates... (Current version: {current_version})[/blue]")
    
    try:
        # Get latest version from GitHub
        with urllib.request.urlopen(f"{raw_url_base}/.version") as response:
            latest_version = response.read().decode("utf-8").strip()
        
        if current_version == latest_version and current_version != "Unknown":
            console.print(f"[green]✅ Wugong Email is already up to date (v{current_version}).[/green]")
            return
            
        console.print(f"[yellow]🔔 A new version is available: [bold]{latest_version}[/bold][/yellow]")
        
        # Fetch and show changelog
        console.print("[blue]📄 Fetching what's new...[/blue]")
        with urllib.request.urlopen(f"{raw_url_base}/CHANGELOG.md") as response:
            changelog_content = response.read().decode("utf-8")
            
        # Extract version blocks from current to latest
        lines = changelog_content.splitlines()
        display_block = []
        found_any = False
        
        # We want to show everything from latest down to (but not including) current_version
        # If current_version is Unknown, show only the latest version
        version_count = 0
        for line in lines:
            if line.startswith("## ["):
                version_match = line.split("[")[1].split("]")[0]
                
                # Stop if we reached the current version
                if version_match == current_version:
                    break
                
                # If current_version is Unknown, we only show the first (latest) version block
                if current_version == "Unknown" and version_count >= 1:
                    break
                    
                version_count += 1
                found_any = True
            
            # Only start adding lines once we've found the first version header
            if found_any:
                display_block.append(line)
        
        if display_block:
            console.print("\n" + "=" * 40)
            console.print(Markdown("\n".join(display_block)))
            console.print("=" * 40 + "\n")
        
        if not questionary.confirm(f"Do you want to update to v{latest_version}?").ask():
            console.print("[blue]Update cancelled.[/blue]")
            return
            
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not check for updates online: {e}[/yellow]")
        console.print("[blue]Attempting to update via local script...[/blue]")

    # Run the update script
    script_path = os.path.join(install_dir, "update.sh")
    if os.name == 'nt':
        script_path = os.path.join(install_dir, "update.ps1")
        # Pass -yes to skip the confirmation in the script
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path, "-yes"])
    else:
        # Pass --yes to skip the confirmation in the script
        subprocess.run(["bash", script_path, "--yes"])

def handle_uninstall():
    install_dir = os.path.expanduser("~/.wugong")
    script_path = os.path.join(install_dir, "uninstall.sh")
    if os.name == 'nt':
        script_path = os.path.join(install_dir, "uninstall.ps1")
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path])
    else:
        subprocess.run(["bash", script_path])

def main():
    parser = argparse.ArgumentParser(description="Wugong Email CLI Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List accounts or emails")
    list_parser.add_argument("account", nargs="?", help="Friendly name of the account to list emails from (use 'all' for all accounts)")
    list_parser.add_argument("--limit", "-l", type=int, help="Number of emails to list per account (default from config)")
    list_parser.add_argument("--all", action="store_true", help="List all available emails")
    list_parser.add_argument("--keyword", "-k", help="Search by keyword in subject or body")
    list_parser.add_argument("--from-user", "-f", help="Search by sender's email or name")
    list_parser.add_argument("--since", help="Search emails since date (e.g., 01-Jan-2024)")
    list_parser.add_argument("--before", help="Search emails before date (e.g., 31-Dec-2024)")
    list_parser.add_argument("--local", action="store_true", help="Only query from local cache, do not use IMAP")

    # Read command
    read_parser = subparsers.add_parser("read", help="Read a specific email")
    read_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    read_parser.add_argument("--id", "-i", required=True, help="Email ID to read")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a specific email")
    delete_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    delete_parser.add_argument("--id", "-i", required=True, help="Email ID to delete")

    # Send command
    send_parser = subparsers.add_parser("send", help="Send an email")
    send_parser.add_argument("--account", "-a", help="Account name (uses default if not specified)")
    send_parser.add_argument("--to", "-t", required=True, help="Recipient email address")
    send_parser.add_argument("--subject", "-s", required=True, help="Email subject")
    send_parser.add_argument("--body", "-b", help="Email body content")
    send_parser.add_argument("--attach", nargs="+", help="Paths to files to attach")

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

    # Email Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync latest emails from server")
    sync_parser.add_argument("account", nargs="?", help="Friendly name of the account to sync (use 'all' for all accounts)")
    sync_parser.add_argument("--limit", "-l", type=int, help="Number of emails to sync per account (default from config)")
    sync_parser.add_argument("--all", action="store_true", help="Sync all emails from server")

    # Upgrade command (code update)
    subparsers.add_parser("upgrade", help="Update Wugong Email code to the latest version")

    # Uninstall command
    subparsers.add_parser("uninstall", help="Uninstall Wugong Email")

    # Init command
    subparsers.add_parser("init", help="Initialize configuration, encryption, and sync schedule")

    # Configure command
    subparsers.add_parser("configure", help="Modify settings like sync interval")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        manager = MailManager()
    except Exception as e:
        console.print(f"[red]Error initializing MailManager: {e}[/red]")
        return

    match args.command:
        case "init":
            handle_init(args, manager)
        case "configure":
            handle_configure(args, manager)
        case "list":
            handle_list(args, manager)
        case "read":
            handle_read(args, manager)
        case "delete":
            handle_delete(args, manager)
        case "send":
            handle_send(args, manager)
        case "account":
            handle_account(args, manager, account_parser)
        case "sync":
            handle_sync(args, manager)
        case "upgrade":
            handle_upgrade()
        case "uninstall":
            handle_uninstall()
        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
