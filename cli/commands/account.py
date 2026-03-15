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
        print(f"Testing connection to {imap_server}:{imap_port} ({tls_method})...")
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

    encrypt_enabled = current_config.get("general", {}).get("encryption_enabled") or current_config.get("general", {}).get("encrypt_emails")
    salt_val = config.get_salt(current_config)

    try:
        if non_interactive:
            # === Non-Interactive Flow ===
            if not friendly_name:
                raise ValueError("Friendly name is required in non-interactive mode.")
            if not username:
                raise ValueError("Email Account (username) is required in non-interactive mode.")
            
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
            newly_added.append((account, limit))
            current_config.setdefault("accounts", []).append(account)
            config.save_config(current_config, config_path)
            return newly_added, encryption_password

        # === Interactive Flow ===
        while True:
            print("\n=== Add New Email Account ===")

            is_default = len(current_config.get("accounts", [])) == 0
            if (friendly_name := questionary.text("Friendly Name (e.g., 'Work Gmail'):", default="default" if is_default else "").ask()) is None:
                raise KeyboardInterrupt

            if (provider := questionary.select("Select your email provider:", choices=list(EMAIL_PROVIDERS.keys()), default="other").ask()) is None:
                raise KeyboardInterrupt
            
            provider_info = EMAIL_PROVIDERS.get(provider, EMAIL_PROVIDERS["other"])
            if provider_info["hint"]:
                print(f"\n[!] {provider_info['hint']}\n")

            if (login_method := questionary.select("Choose login method:", choices=provider_info["auth_methods"], default=provider_info["auth_methods"][0]).ask()) is None:
                raise KeyboardInterrupt

            if (username := questionary.text("Email Account (e.g. yourname@example.com):").ask()) is None:
                raise KeyboardInterrupt
            if not username:
                print("Email Account is required.")
                continue

            if (imap_server := questionary.text("IMAP Server:", default=provider_info["imap_server"]).ask()) is None:
                raise KeyboardInterrupt
            
            if (imap_tls_method := questionary.select("IMAP TLS Method:", choices=["SSL/TLS", "STARTTLS", "Plain"], default=provider_info.get("imap_tls_method", "SSL/TLS")).ask()) is None:
                raise KeyboardInterrupt

            suggested_imap_port = provider_info.get("imap_port") or (993 if imap_tls_method == "SSL/TLS" else 143)
            if (imap_port_str := questionary.text("IMAP Port:", default=str(suggested_imap_port)).ask()) is None:
                raise KeyboardInterrupt
            imap_port = int(imap_port_str)
            
            if (smtp_server := questionary.text("SMTP Server:", default=provider_info["smtp_server"]).ask()) is None:
                raise KeyboardInterrupt
            
            if (smtp_tls_method := questionary.select("SMTP TLS Method:", choices=["SSL/TLS", "STARTTLS", "Plain"], default=provider_info.get("smtp_tls_method", "SSL/TLS")).ask()) is None:
                raise KeyboardInterrupt

            suggested_smtp_port = provider_info.get("smtp_port") or (465 if smtp_tls_method == "SSL/TLS" else 587 if smtp_tls_method == "STARTTLS" else 25)
            if (smtp_port_str := questionary.text("SMTP Port:", default=str(suggested_smtp_port)).ask()) is None:
                raise KeyboardInterrupt
            smtp_port = int(smtp_port_str)

            if encryption_password is None:
                encryption_password = config.get_verified_password(current_config, args, prompt_text="Enter your encryption password to encrypt new account credentials:")

            auth_details = {}
            access_token = ""
            password_val = None
            
            match login_method:
                case "Account/Password":
                    pwd_label = "Authorization Code:" if "Authorization Code" in provider_info["hint"] else "Email Password (or App Password):"
                    if (password_val := questionary.password(pwd_label).ask()) is None:
                        raise KeyboardInterrupt
                    
                    auth_details = {
                        "username": username,
                        "password": encrypt_data(password_val, encryption_password, salt_val) if encrypt_enabled else password_val
                    }
                case "OAuth2":
                    if (client_id := questionary.text("OAuth2 Client ID:").ask()) is None or (client_secret := questionary.password("OAuth2 Client Secret:").ask()) is None:
                        raise KeyboardInterrupt
                    
                    auth_url = questionary.text("OAuth2 Authorization URL:", default=provider_info.get("auth_url", "")).ask()
                    token_url = questionary.text("OAuth2 Token URL:", default=provider_info.get("token_url", "")).ask()
                    scopes_input = questionary.text("OAuth2 Scopes (comma separated):", default=",".join(provider_info.get("scopes", []))).ask()
                    if scopes_input is None: raise KeyboardInterrupt
                    scopes = [s.strip() for s in scopes_input.split(",") if s.strip()]
                    redirect_uri = questionary.text("Redirect URI:", default="http://localhost:5000/").ask()
                    
                    if any(v is None for v in [auth_url, token_url, scopes, redirect_uri]):
                        raise KeyboardInterrupt
                        
                    refresh_token_val = ""
                    if (auto_auth := questionary.confirm("Start local server to automatically fetch tokens?").ask()) is None:
                        raise KeyboardInterrupt
                    
                    if auto_auth:
                        if (token_data := start_oauth_flow(client_id, client_secret, auth_url, token_url, scopes, redirect_uri)) and (token := token_data.get('token')):
                            refresh_token_val = token.get('refresh_token', '')
                            access_token = token.get('access_token', '')
                            if (detected_email := token_data.get('user_email')) and detected_email != username:
                                if (use_detected := questionary.confirm(f"Detected email '{detected_email}' differs from '{username}'. Use detected email?").ask()) is None:
                                    raise KeyboardInterrupt
                                if use_detected:
                                    username = detected_email
                            print(f"\nSuccessfully obtained tokens!")
                        else:
                            print("Failed to obtain tokens automatically. You can enter them manually.")
                    
                    if not refresh_token_val:
                        if (refresh_token_val := questionary.text("OAuth2 Refresh Token (optional):").ask()) is None:
                            raise KeyboardInterrupt
                    
                    if encrypt_enabled:
                        auth_details = {
                            "username": username,
                            "client_id": encrypt_data(client_id, encryption_password, salt_val),
                            "client_secret": encrypt_data(client_secret, encryption_password, salt_val),
                            "auth_url": auth_url,
                            "token_url": token_url,
                            "redirect_uri": redirect_uri,
                            "scopes": scopes,
                            "refresh_token": encrypt_data(refresh_token_val, encryption_password, salt_val) if refresh_token_val else "",
                            "access_token": encrypt_data(access_token, encryption_password, salt_val) if access_token else ""
                        }
                    else:
                        auth_details = {
                            "username": username, "client_id": client_id, "client_secret": client_secret,
                            "auth_url": auth_url, "token_url": token_url, "redirect_uri": redirect_uri,
                            "scopes": scopes, "refresh_token": refresh_token_val, "access_token": access_token
                        }

            account = {
                "friendly_name": friendly_name,
                "login_method": login_method,
                "imap_server": imap_server,
                "imap_port": imap_port,
                "imap_tls_method": imap_tls_method,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "smtp_tls_method": smtp_tls_method,
                "auth": auth_details
            }
            
            # Connection Test
            success, msg = True, ""
            match login_method:
                case "Account/Password":
                    success, msg = test_imap_connection(imap_server, imap_port, username, password=password_val, tls_method=imap_tls_method)
                case "OAuth2":
                    if access_token:
                        success, msg = test_imap_connection(imap_server, imap_port, username, access_token=access_token, tls_method=imap_tls_method)
                    else:
                        print("Skipping connection test for manual OAuth2 (no access token provided yet).")

            if not success:
                from rich import print as rprint
                rprint(f"[red]❌ Connection test failed: {msg}[/red]")
                if (retry := questionary.confirm("Do you want to re-enter credentials?").ask()) is None:
                    raise KeyboardInterrupt
                if retry:
                    continue
                print("Account not added.")
            else:
                print("✅ Connection test successful!")

                if (sync_limit_input := questionary.text(f"Number of latest emails to download during initial sync for '{friendly_name}' (e.g., 20, 50. Enter 'all' for everything):", default="20").ask()) is None:
                    raise KeyboardInterrupt
                limit = -1 if sync_limit_input.lower() == "all" else int(sync_limit_input) if sync_limit_input.isdigit() else 20

                account["sync_limit"] = limit
                newly_added.append((account, limit))
                current_config.setdefault("accounts", []).append(account)
            
            if (add_another := questionary.confirm("Add another account?").ask()) is None:
                raise KeyboardInterrupt
            if not add_another:
                break

        config.save_config(current_config, config_path)
        print(f"\nConfiguration saved to {config_path} with {len(current_config['accounts'])} account(s)!")
        return newly_added, encryption_password

    except KeyboardInterrupt:
        new_accounts_count = len(current_config.get("accounts", [])) - original_accounts_count
        if new_accounts_count > 0:
            config.save_config(current_config, config_path)
            print(f"\n[!] Configuration interrupted. {new_accounts_count} new account(s) were saved to {config_path}.")
            return newly_added, encryption_password
        print("\n[!] Configuration cancelled. No changes were made.")
        return [], None
    except Exception as e:
        print(f"\n❌ Error: {e}")
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
                # Reload manager to get new accounts
                manager = MailManager()
                try:
                    encryption_password = config.get_verified_password(manager.config, args, "Enter encryption password to start initial sync:")
                except ValueError as e:
                    console.print(f"[red]Error: {e}[/red]")
                    return

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
                        task = progress.add_task(f"Initial sync for '{account_name}'...", total=limit if limit > 0 else 100)
                        
                        def update_progress(current, total, description=None):
                            progress.update(task, completed=current, total=total)
                        
                        try:
                            manager.syncer.sync_emails(acc, encryption_password, limit=limit, is_initial_sync=True, progress_callback=update_progress)
                            console.print(f"[green]✅ {account_name}: Successfully synced emails.[/green]")
                        except Exception as e:
                            console.print(f"[red]❌ {account_name}: Initial sync failed: {e}[/red]")
            
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
