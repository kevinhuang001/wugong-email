import sys
import re
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
    def render_header(title: str, subtitle: str | None = None) -> None:
        """Renders a full-width centered header with optional subtitle."""
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
    def render_email_table(emails: list[Email | dict[str, Any]], show_folder: bool = True, show_header: bool = True, verbose: bool = False) -> None:
        """Renders a list of emails in a formatted table."""
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
    def render_email_content(email_data: Email | dict[str, Any], account_name: str) -> None:
        """Renders full email content in a panel."""
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
