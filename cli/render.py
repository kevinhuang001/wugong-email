import sys
import re
import json
import logging
from typing import Any, cast
from email.utils import parsedate_to_datetime
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from mail.storage_manager import Email

console = Console()

class CLIRenderer:
    """Handles all Rich-based UI rendering logic."""
    
    @staticmethod
    def render_header(title: str, subtitle: str | None = None, json_output: bool = False) -> None:
        """Renders a full-width centered header with optional subtitle."""
        if json_output:
            return
            
        t = Table(show_header=False, show_edge=False, box=None, expand=True, padding=0)
        t.add_column(justify="center", style="on black")
        t.add_row(title)
        console.print(t)
        
        if subtitle:
            st = Table(show_header=False, show_edge=False, box=None, expand=True, padding=0)
            st.add_column(justify="center", style="on black")
            st.add_row(subtitle)
            console.print(st)

    @staticmethod
    def render_email_table(emails: list[Email | dict[str, Any]], show_folder: bool = True, show_header: bool = True, verbose: bool = False, json_output: bool = False, data: dict[str, Any] | None = None) -> None:
        """Renders a list of emails in a formatted table or JSON."""
        if json_output:
            results = []
            for em in emails:
                if isinstance(em, Email):
                    results.append(em.to_dict())
                else:
                    results.append(em)
            
            output: Any = results
            if data:
                output = {"emails": results}
                output.update(data)
                
            sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
            return

        table = Table(show_lines=False, box=None, expand=True, show_header=show_header, header_style="bold white")
        table.add_column("", justify="center", width=1) # Status
        table.add_column("ID", style="cyan", justify="right", width=6)
        
        if verbose and show_folder:
            table.add_column("Folder", style="yellow", width=15)
            
        table.add_column("From", style="magenta", width=20)
        
        if verbose:
            table.add_column("Email", style="blue", width=25)
            
        table.add_column("Subject", style="white", ratio=1)
        table.add_column("Time", style="green", width=19)

        for em in emails:
            match em:
                case Email() as e:
                    is_seen, eid, folder, from_user, from_email, subject, date_val = e.seen, e.uid, getattr(e, "folder", "INBOX"), e.sender, e.sender_email, e.subject, e.date
                case dict() as d:
                    is_seen, eid, folder, from_user, from_email, subject, date_val = d.get("seen", True), d.get("id", ""), d.get("folder", "INBOX"), d.get("from", ""), d.get("from_email", ""), d.get("subject", ""), d.get("date", "")
                case _: continue
            
            status_mark = "" if is_seen else "*"
            
            # Clean for single-line display
            subject = (subject or "").replace("\n", " ").replace("\r", "")
            from_user = (from_user or "").replace("\n", " ").replace("\r", "")
            from_email = (from_email or "").replace("\n", " ").replace("\r", "")
            
            display_time = date_val
            try:
                dt = parsedate_to_datetime(date_val)
                display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            
            row_data = [status_mark, str(eid)]
            if verbose and show_folder:
                row_data.append(folder)
            
            row_data.append(from_user)
            
            if verbose:
                row_data.append(from_email)
                
            row_data.extend([subject, display_time])
            table.add_row(*row_data)
        
        console.print(table)
        console.print("-" * (console.width or 80))

    @staticmethod
    def render_email_content(email_data: Email | dict[str, Any], account_name: str, json_output: bool = False) -> None:
        """Renders full email content in a panel or JSON."""
        if json_output:
            if isinstance(email_data, Email):
                sys.stdout.write(json.dumps(email_data.to_dict(), indent=2, ensure_ascii=False) + "\n")
            else:
                sys.stdout.write(json.dumps(email_data, indent=2, ensure_ascii=False) + "\n")
            return

        match email_data:
            case Email() as e:
                subject, sender, sender_email, date_str, content, attachments, eid, folder = e.subject, e.sender, e.sender_email, e.date, e.content, e.attachments, e.uid, getattr(e, "folder", "INBOX")
            case dict() as d:
                subject, sender, sender_email, date_str, content, attachments, eid, folder = d.get("subject", "No Subject"), d.get("from", "Unknown"), d.get("from_email", ""), d.get("date", "Unknown"), d.get("content", ""), d.get("attachments", []), d.get("id", ""), d.get("folder", "INBOX")
            case _: return

        header_table = Table.grid(padding=(0, 1))
        header_table.add_column(style="bold cyan", justify="right")
        header_table.add_column()
        
        header_table.add_row("Subject:", f"[bold white]{subject}[/bold white]")
        header_table.add_row("From:", f"{sender} <{sender_email}>")
        header_table.add_row("Date:", f"{date_str}")
        header_table.add_row("Folder:", f"{folder}")
        
        if attachments:
            header_table.add_row("Attachments:", f"[yellow]📎 {', '.join(attachments)}[/yellow]")

        display_content = Group(
            header_table,
            f"\n[dim]{'─' * (console.width - 10)}[/dim]\n",
            content
        )
        
        panel = Panel(
            display_content,
            title=f"[bold green]Email {eid}[/bold green]",
            subtitle=f"[dim]Account: {account_name}[/dim]",
            border_style="blue",
            padding=(1, 2),
            expand=False
        )
        console.print(panel)

    @staticmethod
    def render_accounts_table(accounts_data: list[dict[str, Any]], verbose: bool = False, json_output: bool = False) -> None:
        """Renders a list of configured accounts."""
        if json_output:
            sys.stdout.write(json.dumps(accounts_data, indent=2, ensure_ascii=False) + "\n")
            return

        table = Table(title="Configured Email Accounts", show_footer=True)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Friendly Name", style="magenta")
        table.add_column("Email Address", style="blue")
        table.add_column("Cached", style="green", justify="right")
        table.add_column("Unseen", style="bold yellow", justify="right")
        
        if verbose:
            table.add_column("Server Total", style="blue", justify="right")
            table.add_column("Server Unseen", style="bold red", justify="right")
            table.add_column("Method", style="green")
            table.add_column("IMAP Server", style="yellow")

        total_cached = 0
        total_unseen = 0
        total_srv_msg = 0
        total_srv_unseen = 0

        for idx, acc in enumerate(accounts_data, 1):
            row = [
                str(idx),
                acc.get("friendly_name", "N/A"),
                acc.get("username", "N/A"),
                str(acc.get("cached_count", 0)),
                str(acc.get("unseen_count", 0))
            ]
            total_cached += acc.get("cached_count", 0)
            total_unseen += acc.get("unseen_count", 0)

            if verbose:
                row.extend([
                    str(acc.get("server_total", "N/A")),
                    str(acc.get("server_unseen", "N/A")),
                    acc.get("login_method", "N/A"),
                    f"{acc.get('imap_server', 'N/A')}:{acc.get('imap_port', 'N/A')}"
                ])
                if isinstance(acc.get("server_total"), int):
                    total_srv_msg += acc.get("server_total", 0)
                if isinstance(acc.get("server_unseen"), int):
                    total_srv_unseen += acc.get("server_unseen", 0)
            
            table.add_row(*row)

        table.columns[0].footer = "Total"
        table.columns[3].footer = str(total_cached)
        table.columns[4].footer = str(total_unseen)
        if verbose:
            table.columns[5].footer = str(total_srv_msg)
            table.columns[6].footer = str(total_srv_unseen)
        
        console.print(table)

    @staticmethod
    def render_folders_list(folders: list[str], json_output: bool = False) -> None:
        """Renders a list of folders."""
        if json_output:
            sys.stdout.write(json.dumps(folders, indent=2, ensure_ascii=False) + "\n")
            return
        
        for folder in folders:
            console.print(f"- {folder}")

    @staticmethod
    def render_folders_table(folders_data: list[dict[str, Any]], account_name: str, verbose: bool = False, json_output: bool = False) -> None:
        """Renders a list of folders with stats."""
        if json_output:
            sys.stdout.write(json.dumps(folders_data, indent=2, ensure_ascii=False) + "\n")
            return

        table = Table(title=f"Folders for {account_name}")
        table.add_column("Folder Name", style="cyan")
        table.add_column("Cached", justify="right", style="green")
        table.add_column("Unseen", justify="right", style="bold yellow")
        
        if verbose:
            table.add_column("Total (Server)", justify="right", style="blue")
            table.add_column("Unseen (Server)", justify="right", style="bold yellow")
            
        for f in folders_data:
            row = [
                f.get("name", "N/A"),
                str(f.get("cached_count", 0)),
                str(f.get("cached_unseen", 0))
            ]
            if verbose:
                row.extend([
                    str(f.get("server_total", 0)),
                    str(f.get("server_unseen", 0))
                ])
            table.add_row(*row)
            
        console.print(table)

    @staticmethod
    def render_message(message: str, type: str = "info", json_output: bool = False, data: dict[str, Any] | None = None) -> None:
        """Renders a status or notification message."""
        if json_output:
            output = {"status": type, "message": message}
            if data:
                output.update(data)
            sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
            return
        
        logger = logging.getLogger("wugong.cli")
        match type:
            case "success":
                logger.info(f"[green]✅ {message}[/green]")
            case "error":
                logger.error(f"[red]❌ {message}[/red]")
            case "warning":
                logger.warning(f"[yellow]⚠️ {message}[/yellow]")
            case _:
                logger.info(message)
