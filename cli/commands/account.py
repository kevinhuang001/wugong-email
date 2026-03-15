import argparse
import sys
import imaplib
from typing import Any
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
import questionary

import config
from mail import MailManager
from crypto_utils import encrypt_data
from oauth2 import start_oauth_flow

console = Console()

EMAIL_PROVIDERS = {
    "gmail": {
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "imap_tls_method": "SSL/TLS",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 465,
        "smtp_tls_method": "SSL/TLS",
        "auth_methods": ["OAuth2", "Account/Password"],
        "auth_url": "https://accounts.google.com/o/oauth2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://mail.google.com/"],
        "hint": "Note: Gmail requires an 'App Password' if using Account/Password and 2FA is enabled."
    },
    "outlook": {
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "imap_tls_method": "SSL/TLS",
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "smtp_tls_method": "STARTTLS",
        "auth_methods": ["OAuth2", "Account/Password"],
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": [
            "openid",
            "https://outlook.office.com/IMAP.AccessAsUser.All",
            "https://outlook.office.com/SMTP.Send",
            "offline_access"
        ],
        "hint": "Note: Outlook may require an 'App Password' if 2FA is enabled."
    },
    "qq": {
        "imap_server": "imap.qq.com",
        "imap_port": 993,
        "imap_tls_method": "SSL/TLS",
        "smtp_server": "smtp.qq.com",
        "smtp_port": 465,
        "smtp_tls_method": "SSL/TLS",
        "auth_methods": ["Account/Password"],
        "auth_url": "",
        "token_url": "",
        "scopes": [],
        "hint": "Note: QQ Mail REQUIRES an 'Authorization Code' instead of your regular password."
    },
    "163": {
        "imap_server": "imap.163.com",
        "imap_port": 993,
        "imap_tls_method": "SSL/TLS",
        "smtp_server": "smtp.163.com",
        "smtp_port": 465,
        "smtp_tls_method": "SSL/TLS",
        "auth_methods": ["Account/Password"],
        "auth_url": "",
        "token_url": "",
        "scopes": [],
        "hint": "Note: 163 Mail REQUIRES an 'Authorization Code' instead of your regular password."
    },
    "other": {
        "imap_server": "",
        "imap_port": 993,
        "imap_tls_method": "SSL/TLS",
        "smtp_server": "",
        "smtp_port": 465,
        "smtp_tls_method": "SSL/TLS",
        "auth_methods": ["Account/Password", "OAuth2"],
        "auth_url": "",
        "token_url": "",
        "scopes": [],
        "hint": ""
    }
}

def test_imap_connection(imap_server: str, imap_port: int, username: str, password: str | None = None, access_token: str | None = None, tls_method: str = "SSL/TLS", timeout: int = 30) -> tuple[bool, str]:
    """Tests if we can connect and login to the IMAP server."""
    try:
        # Note: We don't print here anymore as the caller (wizard) uses console.status or similar
        match tls_method:
            case "SSL/TLS":
                mail = imaplib.IMAP4_SSL(imap_server, imap_port, timeout=timeout)
            case "STARTTLS":
                mail = imaplib.IMAP4(imap_server, imap_port, timeout=timeout)
                mail.starttls()
            case _:
                mail = imaplib.IMAP4(imap_server, imap_port, timeout=timeout)

        if access_token:
            # OAuth2 authentication (XOAUTH2)
            auth_string = f"user={username}\x01auth=Bearer {access_token}\x01\x01"
            mail.authenticate('XOAUTH2', lambda x: auth_string)
        else:
            # Password authentication
            mail.login(username, password)

        mail.logout()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def account_add_wizard(
    args: argparse.Namespace | None = None,
    friendly_name: str | None = None,
    provider: str | None = None,
    login_method: str | None = None,
    username: str | None = None,
    imap_server: str | None = None,
    imap_port: int | None = None,
    imap_tls_method: str | None = None,
    smtp_server: str | None = None,
    smtp_port: int | None = None,
    smtp_tls_method: str | None = None,
    password: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    auth_url: str | None = None,
    token_url: str | None = None,
    scopes: list[str] | None = None,
    redirect_uri: str | None = None,
    sync_limit: str | int | None = None,
    non_interactive: bool = False
) -> tuple[list, str | None]:
    """Interactive or non-interactive wizard to add one or more email accounts."""
    config_path = config.get_config_path()
    current_config = config.load_config(config_path)
    original_accounts_count = len(current_config.get("accounts", []))
    newly_added = []
    encryption_password = None

    # 1. Validation Helpers
    def is_friendly_name_taken(name):
        return any(acc.get("friendly_name") == name for acc in current_config.get("accounts", [])) or \
               any(item[0].get("friendly_name") == name for item in newly_added)

    def is_username_taken(uname):
        return any(acc.get("auth", {}).get("username") == uname for acc in current_config.get("accounts", [])) or \
               any(item[0].get("auth", {}).get("username") == uname for item in newly_added)

    encrypt_enabled = current_config.get("general", {}).get("encryption_enabled") or current_config.get("general", {}).get("encrypt_emails")
    salt_val = config.get_salt(current_config)

    try:
        if non_interactive:
            # === Non-Interactive Flow (Single Account) ===
            if not friendly_name:
                raise ValueError("Friendly name is required in non-interactive mode.")
            if not username:
                raise ValueError("Email Account (username) is required in non-interactive mode.")
            
            # Check for unique friendly name
            if is_friendly_name_taken(friendly_name):
                raise ValueError(f"Account with friendly name '{friendly_name}' already exists.")

            # Warn for duplicate email address
            if is_username_taken(username):
                console.print(f"[yellow]Warning: An account with username '{username}' is already configured.[/yellow]")

            # Pre-check encryption password if encryption is enabled
            encryption_password = config.get_verified_password(current_config, args)

            provider = provider or "other"
            provider_info = EMAIL_PROVIDERS.get(provider, EMAIL_PROVIDERS["other"])
            login_method = login_method or "Account/Password"
            imap_server = imap_server or provider_info["imap_server"]
            imap_tls_method = imap_tls_method or provider_info.get("imap_tls_method", "SSL/TLS")
            imap_port = imap_port or provider_info.get("imap_port") or (993 if imap_tls_method == "SSL/TLS" else 143)
            smtp_server = smtp_server or provider_info["smtp_server"]
            smtp_tls_method = smtp_tls_method or provider_info.get("smtp_tls_method", "SSL/TLS")
            smtp_port = smtp_port or provider_info.get("smtp_port") or (465 if smtp_tls_method == "SSL/TLS" else 587 if smtp_tls_method == "STARTTLS" else 25)

            auth_details = {}
            match login_method:
                case "Account/Password":
                    if not password:
                        raise ValueError("Password is required in non-interactive mode for Account/Password login.")
                    auth_details = {
                        "username": username,
                        "password": encrypt_data(password, encryption_password, salt_val) if encrypt_enabled else password
                    }
                case "OAuth2":
                    if not client_id or not client_secret:
                        raise ValueError("Client ID and Client Secret are required in non-interactive mode for OAuth2 login.")
                    auth_url = auth_url or provider_info.get("auth_url", "")
                    token_url = token_url or provider_info.get("token_url", "")
                    scopes = scopes or provider_info.get("scopes", [])
                    redirect_uri = redirect_uri or "http://localhost:5000/"
                    # Use password as refresh token in non-interactive OAuth2 if needed
                    refresh_token_val = password or ""
                    if not refresh_token_val:
                        raise ValueError("Refresh Token is required in non-interactive mode for OAuth2 login (provide via --password).")
                    
                    if encrypt_enabled:
                        auth_details = {
                            "username": username,
                            "client_id": encrypt_data(client_id, encryption_password, salt_val),
                            "client_secret": encrypt_data(client_secret, encryption_password, salt_val),
                            "auth_url": auth_url,
                            "token_url": token_url,
                            "redirect_uri": redirect_uri,
                            "scopes": scopes,
                            "refresh_token": encrypt_data(refresh_token_val, encryption_password, salt_val),
                            "access_token": ""
                        }
                    else:
                        auth_details = {
                            "username": username, "client_id": client_id, "client_secret": client_secret,
                            "auth_url": auth_url, "token_url": token_url, "redirect_uri": redirect_uri,
                            "scopes": scopes, "refresh_token": refresh_token_val, "access_token": ""
                        }

            if isinstance(sync_limit, str):
                limit = -1 if sync_limit.lower() == "all" else int(sync_limit) if sync_limit.isdigit() else 20
            else:
                limit = sync_limit if sync_limit is not None else 20

            account = {
                "friendly_name": friendly_name,
                "login_method": login_method,
                "imap_server": imap_server,
                "imap_port": imap_port,
                "imap_tls_method": imap_tls_method,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "smtp_tls_method": smtp_tls_method,
                "auth": auth_details,
                "sync_limit": limit
            }

            # Connection Test for Non-Interactive
            success, msg = True, ""
            if login_method == "Account/Password":
                success, msg = test_imap_connection(imap_server, imap_port, username, password=password, tls_method=imap_tls_method)
            elif login_method == "OAuth2":
                console.print("[yellow]Skipping connection test for non-interactive OAuth2 (requires refresh token exchange).[/yellow]")
            
            if not success:
                console.print(f"[red]❌ Connection test failed for '{friendly_name}': {msg}[/red]")
                raise ValueError(f"Connection test failed for '{friendly_name}': {msg}")

            console.print(f"[green]✅ Connection test successful for '{friendly_name}'![/green]")
            newly_added.append((account, limit))
            return newly_added, encryption_password

        # === Interactive Flow (Multi-Account) ===
        while True:
            console.print("\n[bold cyan]=== Add New Email Account ===[/bold cyan]")

            is_default = len(current_config.get("accounts", [])) == 0
            
            # 1. Friendly Name
            curr_friendly_name = friendly_name
            if curr_friendly_name is None:
                while True:
                    if (curr_friendly_name := questionary.text("Friendly Name (e.g., 'Work Gmail'):", default="default" if is_default else "").ask()) is None:
                        raise KeyboardInterrupt
                    
                    if is_friendly_name_taken(curr_friendly_name):
                        console.print(f"[red]Error: Account with friendly name '{curr_friendly_name}' already exists. Please choose another name.[/red]")
                        curr_friendly_name = None
                        continue
                    break
            else:
                if is_friendly_name_taken(curr_friendly_name):
                    raise ValueError(f"Account with friendly name '{curr_friendly_name}' already exists.")

            # 2. Provider
            curr_provider = provider
            if curr_provider is None:
                if (curr_provider := questionary.select("Select your email provider:", choices=list(EMAIL_PROVIDERS.keys()), default="other").ask()) is None:
                    raise KeyboardInterrupt
            
            provider_info = EMAIL_PROVIDERS.get(curr_provider, EMAIL_PROVIDERS["other"])
            if provider_info["hint"]:
                console.print(f"\n[bold yellow]![/bold yellow] {provider_info['hint']}\n")

            # 3. Login Method
            curr_login_method = login_method
            if curr_login_method is None:
                if (curr_login_method := questionary.select("Choose login method:", choices=provider_info["auth_methods"], default=provider_info["auth_methods"][0]).ask()) is None:
                    raise KeyboardInterrupt

            # 4. Username
            curr_username = username
            if curr_username is None:
                while True:
                    if (curr_username := questionary.text("Email Account (e.g. yourname@example.com):").ask()) is None:
                        raise KeyboardInterrupt
                    
                    if not curr_username:
                        console.print("[red]Email Account is required.[/red]")
                        continue
                    
                    if is_username_taken(curr_username):
                        if not questionary.confirm(f"Warning: An account with username '{curr_username}' is already configured. Add it anyway?").ask():
                            curr_username = None
                            continue
                    break
            else:
                if is_username_taken(curr_username):
                    console.print(f"[yellow]Warning: An account with username '{curr_username}' is already configured.[/yellow]")


            # 5. IMAP Server
            curr_imap_server = imap_server
            if curr_imap_server is None:
                if (curr_imap_server := questionary.text("IMAP Server:", default=provider_info["imap_server"]).ask()) is None:
                    raise KeyboardInterrupt
            
            # 6. IMAP TLS Method
            curr_imap_tls_method = imap_tls_method
            if curr_imap_tls_method is None:
                if (curr_imap_tls_method := questionary.select("IMAP TLS Method:", choices=["SSL/TLS", "STARTTLS", "Plain"], default=provider_info.get("imap_tls_method", "SSL/TLS")).ask()) is None:
                    raise KeyboardInterrupt

            # 7. IMAP Port
            curr_imap_port = imap_port
            if curr_imap_port is None:
                suggested_imap_port = provider_info.get("imap_port") or (993 if curr_imap_tls_method == "SSL/TLS" else 143)
                if (imap_port_str := questionary.text("IMAP Port:", default=str(suggested_imap_port)).ask()) is None:
                    raise KeyboardInterrupt
                curr_imap_port = int(imap_port_str)
            
            # 8. SMTP Server
            curr_smtp_server = smtp_server
            if curr_smtp_server is None:
                if (curr_smtp_server := questionary.text("SMTP Server:", default=provider_info["smtp_server"]).ask()) is None:
                    raise KeyboardInterrupt
            
            # 9. SMTP TLS Method
            curr_smtp_tls_method = smtp_tls_method
            if curr_smtp_tls_method is None:
                if (curr_smtp_tls_method := questionary.select("SMTP TLS Method:", choices=["SSL/TLS", "STARTTLS", "Plain"], default=provider_info.get("smtp_tls_method", "SSL/TLS")).ask()) is None:
                    raise KeyboardInterrupt

            # 10. SMTP Port
            curr_smtp_port = smtp_port
            if curr_smtp_port is None:
                suggested_smtp_port = provider_info.get("smtp_port") or (465 if curr_smtp_tls_method == "SSL/TLS" else 587 if curr_smtp_tls_method == "STARTTLS" else 25)
                if (smtp_port_str := questionary.text("SMTP Port:", default=str(suggested_smtp_port)).ask()) is None:
                    raise KeyboardInterrupt
                curr_smtp_port = int(smtp_port_str)

            # 11. Encryption Password (one-time check)
            if encryption_password is None:
                encryption_password = config.get_verified_password(current_config, args, prompt_text="Enter your encryption password to encrypt new account credentials:")

            auth_details = {}
            access_token = ""
            password_val = password
            
            # 12. Credentials and CONNECTION TEST (The "Test one, Add one" logic)
            success = False
            while not success:
                match curr_login_method:
                    case "Account/Password":
                        if password_val is None:
                            pwd_label = "Authorization Code:" if "Authorization Code" in provider_info["hint"] else "Email Password (or App Password):"
                            if (password_val := questionary.password(pwd_label).ask()) is None:
                                raise KeyboardInterrupt
                        
                        # Test Connection Immediately
                        with console.status(f"[bold green]Testing connection for '{curr_friendly_name}'..."):
                            success, msg = test_imap_connection(curr_imap_server, curr_imap_port, curr_username, password=password_val, tls_method=curr_imap_tls_method)
                        
                        if not success:
                            console.print(f"[red]❌ Connection test failed: {msg}[/red]")
                            if not questionary.confirm("Connection failed. Do you want to re-enter credentials?").ask():
                                console.print("[yellow]Skipping this account.[/yellow]")
                                break # Skip this account
                            password_val = None # Reset password to ask again
                            continue

                        auth_details = {
                            "username": curr_username,
                            "password": encrypt_data(password_val, encryption_password, salt_val) if encrypt_enabled else password_val
                        }
                        
                    case "OAuth2":
                        curr_client_id = client_id
                        curr_client_secret = client_secret
                        curr_auth_url = auth_url
                        curr_token_url = token_url
                        curr_scopes = scopes
                        curr_redirect_uri = redirect_uri

                        if curr_client_id is None or curr_client_secret is None:
                            if (curr_client_id := questionary.text("OAuth2 Client ID:", default=curr_client_id or "").ask()) is None or \
                               (curr_client_secret := questionary.password("OAuth2 Client Secret:").ask()) is None:
                                raise KeyboardInterrupt
                        
                        if curr_auth_url is None:
                            curr_auth_url = questionary.text("OAuth2 Authorization URL:", default=provider_info.get("auth_url", "")).ask()
                        if curr_token_url is None:
                            curr_token_url = questionary.text("OAuth2 Token URL:", default=provider_info.get("token_url", "")).ask()
                        if curr_scopes is None:
                            scopes_input = questionary.text("OAuth2 Scopes (comma separated):", default=",".join(provider_info.get("scopes", []))).ask()
                            if scopes_input is None: raise KeyboardInterrupt
                            curr_scopes = [s.strip() for s in scopes_input.split(",") if s.strip()]
                        if curr_redirect_uri is None:
                            curr_redirect_uri = questionary.text("Redirect URI:", default="http://localhost:5000/").ask()
                        
                        if any(v is None for v in [curr_auth_url, curr_token_url, curr_scopes, curr_redirect_uri]):
                            raise KeyboardInterrupt

                        # OAuth2 flow
                        console.print("[bold cyan]Starting OAuth2 flow in your browser...[/bold cyan]")
                        try:
                            token_data = start_oauth_flow(curr_client_id, curr_client_secret, curr_auth_url, curr_token_url, curr_scopes, curr_redirect_uri)
                            if token_data and (token := token_data.get('token')):
                                refresh_token_val = token.get('refresh_token', '')
                                access_token = token.get('access_token', '')
                                if (detected_email := token_data.get('user_email')) and detected_email != curr_username:
                                    if (use_detected := questionary.confirm(f"Detected email '{detected_email}' differs from '{curr_username}'. Use detected email?").ask()) is None:
                                        raise KeyboardInterrupt
                                    if use_detected:
                                        curr_username = detected_email
                                
                                # Test connection with access token
                                with console.status(f"[bold green]Testing connection for '{curr_friendly_name}'..."):
                                    success, msg = test_imap_connection(curr_imap_server, curr_imap_port, curr_username, access_token=access_token, tls_method=curr_imap_tls_method)
                                
                                if not success:
                                    console.print(f"[red]❌ Connection test failed with obtained tokens: {msg}[/red]")
                                    if not questionary.confirm("Do you want to try OAuth2 again?").ask():
                                        break
                                    continue

                                auth_details = {
                                    "username": curr_username,
                                    "client_id": encrypt_data(curr_client_id, encryption_password, salt_val) if encrypt_enabled else curr_client_id,
                                    "client_secret": encrypt_data(curr_client_secret, encryption_password, salt_val) if encrypt_enabled else curr_client_secret,
                                    "auth_url": curr_auth_url,
                                    "token_url": curr_token_url,
                                    "redirect_uri": curr_redirect_uri,
                                    "scopes": curr_scopes,
                                    "refresh_token": encrypt_data(refresh_token_val, encryption_password, salt_val) if encrypt_enabled else refresh_token_val,
                                    "access_token": ""
                                }
                            else:
                                raise ValueError("Failed to obtain tokens.")
                        except Exception as e:
                            console.print(f"[red]❌ OAuth2 flow failed: {e}[/red]")
                            if not questionary.confirm("OAuth2 failed. Do you want to try again?").ask():
                                break
                            continue

                if success:
                    console.print(f"[green]✅ Connection test successful for '{curr_friendly_name}'![/green]")
                    
                    # 13. Sync Limit
                    curr_sync_limit = sync_limit
                    if curr_sync_limit is None:
                        curr_sync_limit = questionary.text(f"Initial sync limit for '{curr_friendly_name}' (number, or 'all'):", default="20").ask()
                    
                    limit = -1 if str(curr_sync_limit).lower() == "all" else int(curr_sync_limit) if str(curr_sync_limit).isdigit() else 20

                    account = {
                        "friendly_name": curr_friendly_name,
                        "login_method": curr_login_method,
                        "imap_server": curr_imap_server,
                        "imap_port": curr_imap_port,
                        "imap_tls_method": curr_imap_tls_method,
                        "smtp_server": curr_smtp_server,
                        "smtp_port": curr_smtp_port,
                        "smtp_tls_method": curr_smtp_tls_method,
                        "auth": auth_details,
                        "sync_limit": limit
                    }
                    newly_added.append((account, limit))

            # Ask to add another account
            if not questionary.confirm("Add another account?").ask():
                break

            # Reset parameters for next loop iteration
            friendly_name = provider = login_method = username = imap_server = imap_port = imap_tls_method = smtp_server = smtp_port = smtp_tls_method = password = client_id = client_secret = auth_url = token_url = scopes = redirect_uri = sync_limit = None
        
        return newly_added, encryption_password

    except KeyboardInterrupt:
        return newly_added, encryption_password
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        return [], None

def handle_account(args: argparse.Namespace, manager: MailManager, account_parser: argparse.ArgumentParser) -> None:
    """Entry point for 'account' commands."""
    if not args.account_command:
        account_parser.print_help()
        return

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
            newly_added, encryption_password = account_add_wizard(
                args=args,
                friendly_name=args.friendly_name,
                provider=args.provider,
                login_method=args.login_method,
                username=args.username,
                imap_server=args.imap_server,
                imap_port=args.imap_port,
                imap_tls_method=args.imap_tls,
                smtp_server=args.smtp_server,
                smtp_port=args.smtp_port,
                smtp_tls_method=args.smtp_tls,
                password=args.password,
                client_id=args.client_id,
                client_secret=args.client_secret,
                auth_url=args.auth_url,
                token_url=args.token_url,
                scopes=args.scopes.split(",") if args.scopes else None,
                redirect_uri=args.redirect_uri,
                sync_limit=args.sync_limit,
                non_interactive=getattr(args, "non_interactive", False)
            )
            
            if newly_added:
                # 1. BATCH SAVE ALL VERIFIED ACCOUNTS
                for acc, _ in newly_added:
                    manager.accounts.append(acc)
                
                manager.config["accounts"] = manager.accounts
                manager._save_config()
                console.print(f"[green]✅ {len(newly_added)} account(s) configured and saved successfully.[/green]")

                # 2. BATCH INITIAL SYNC
                if encryption_password is None:
                    try:
                        encryption_password = config.get_verified_password(manager.config, args, "Enter encryption password to start initial sync:")
                    except ValueError as e:
                        console.print(f"[red]Error: {e}[/red]")
                        return

                for acc, limit in newly_added:
                    account_name = acc.get("friendly_name")
                    if limit == 0:
                        console.print(f"[yellow]Initial sync for '{account_name}' skipped (limit 0).[/yellow]")
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
                        task = progress.add_task(f"Initial sync for '{account_name}'...", total=limit if limit > 0 else 100)
                        
                        def update_progress(current, total, description=None):
                            progress.update(task, completed=current, total=total)
                        
                        try:
                            emails, metadata = manager.syncer.sync_emails(acc, encryption_password, limit=limit, is_initial_sync=True, progress_callback=update_progress)
                            
                            if metadata.get("is_offline", False):
                                console.print(f"[yellow]⚠️ Initial sync for '{account_name}' failed: {metadata.get('error', 'Connection failed')}.[/yellow]")
                            else:
                                console.print(f"[green]✅ Initial sync for '{account_name}' complete ({len(metadata.get('new_emails', []))} new emails).[/green]")
                                
                        except Exception as e:
                            console.print(f"[red]❌ Error during initial sync for '{account_name}': {e}[/red]")
            
        case "delete":
            if not (account := manager.get_account_by_name(args.name)):
                console.print(f"[red]Error: Account '{args.name}' not found.[/red]")
                return
                
            if getattr(args, "non_interactive", False) or questionary.confirm(f"Are you sure you want to delete account '{args.name}'?").ask():
                manager.accounts = [acc for acc in manager.accounts if acc.get("friendly_name") != args.name]
                manager.config["accounts"] = manager.accounts
                manager._save_config()
                console.print(f"[green]Successfully deleted account '{args.name}'.[/green]")
            else:
                console.print("[yellow]Deletion cancelled.[/yellow]")
        case _:
            account_parser.print_help()
