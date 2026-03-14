import argparse
import sys
import re
import logging
import webbrowser
import tempfile
import os
import html
from rich.console import Console
import questionary
from mail import MailManager
from mail.storage import Email
from cli.renderer import CLIRenderer
import config

logger = logging.getLogger("cli.read")
console = Console()

def handle_read(args: argparse.Namespace, manager: MailManager) -> None:
    if not (account := manager.get_account_by_name(args.account or "default")):
        console.print(f"[red]Error: Account '{args.account or 'default'}' not found.[/red]")
        return

    account_name = account.get("friendly_name", "default")
    password = ""
    if (manager.encryption_enabled or manager.config.get("general", {}).get("encrypt_emails", False)) and not (password := config.get_encryption_password(args, f"Enter encryption password for '{account_name}':")):
        return

    folder = getattr(args, "folder", "INBOX") or "INBOX"

    with console.status(f"[bold green]Fetching content for email {args.id} from {folder} via {account_name}...") as status:
        try:
            match manager.reader.read_email(account, password, args.id, folder=folder):
                case None:
                    console.print(f"[yellow]No content found for email {args.id} in {folder}.[/yellow]")
                case str() as err:
                    console.print(f"[red]Error: {err}[/red]")
                case Email() as email_data:
                    status.stop()
                    
                    # Determine display mode
                    mode = None
                    if args.raw: mode = "raw"
                    elif args.text: mode = "text"
                    elif args.browser: mode = "browser"
                    
                    if not mode and sys.stdin.isatty():
                        mode = questionary.select(
                            "Choose how to view this email:",
                            choices=[
                                questionary.Choice("Text (view extracted content)", "text"),
                                questionary.Choice("Raw (view original source)", "raw"),
                                questionary.Choice("Browser (open in web browser)", "browser"),
                                questionary.Choice("Cancel", "cancel")
                            ]
                        ).ask()
                    
                    if mode == "cancel" or not mode:
                        return

                    if mode == "browser":
                        try:
                            # If content is not HTML, wrap it in basic HTML to preserve formatting
                            is_html = "html" in email_data.content_type.lower() or "<html" in email_data.content[:200].lower()
                            display_content = email_data.content
                            if not is_html:
                                escaped_content = html.escape(email_data.content)
                                display_content = f"<html><body><pre style='white-space: pre-wrap; font-family: monospace;'>{escaped_content}</pre></body></html>"

                            # Create a temporary file to open in browser
                            with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode='w', encoding='utf-8') as f:
                                f.write(display_content)
                                temp_path = f.name
                            
                            # Use file:// URL for local file
                            file_url = f"file://{os.path.abspath(temp_path)}"
                            if not webbrowser.open(file_url):
                                logger.warning("No browser found to open the email.")
                                console.print("[yellow]Warning: Could not open browser. No default browser detected.[/yellow]")
                            else:
                                console.print(f"[green]Email opened in browser: {file_url}[/green]")
                        except Exception as e:
                            logger.error(f"Failed to open browser: {e}")
                            console.print(f"[red]Error opening browser: {e}[/red]")
                        return

                    if mode == "text":
                        # If content seems like HTML, extract text
                        is_html = "html" in email_data.content_type.lower() or "<html" in email_data.content[:200].lower()
                        if is_html:
                            text = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', email_data.content, flags=re.DOTALL | re.IGNORECASE)
                            text = re.sub(r'<[^<]+?>', '', text)
                            # Unescape common HTML entities
                            text = html.unescape(text)
                            text = re.sub(r'\n\s*\n', '\n\n', text)
                            email_data.content = f"[Note: Extracted from HTML]\n\n{text.strip()}"
                    
                    # For 'raw' or 'text' (if already plain text), render in CLI
                    CLIRenderer.render_email_content(email_data, account_name)
        except Exception as e:
            logger.error(f"Error reading email {args.id}: {e}")
            console.print(f"[red]Error: {e}[/red]")
