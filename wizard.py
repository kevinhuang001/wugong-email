import base64
import json
import time
import questionary
import threading
import webbrowser
import logging
import imaplib
import platform
import subprocess
from pathlib import Path
from flask import Flask, request
from requests_oauthlib import OAuth2Session
from crypto_utils import generate_salt
import config

# Disable Flask/Werkzeug default logs to keep terminal clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Allow insecure transport for local testing if needed (though usually https is required by providers)
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Relax scope matching for providers like Microsoft that might return different scopes than requested
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

CONFIG_FILE = "config.toml"

EMAIL_PROVIDERS = {
    "Gmail": {
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
    "Outlook": {
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
    "QQ Mail": {
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
    "163 Mail": {
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
    "Other": {
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

def start_oauth_flow(client_id: str, client_secret: str, auth_url: str, token_url: str, scopes: list[str], redirect_uri: str) -> dict:
    """Starts a local server to handle OAuth2 callback and returns the token."""
    app = Flask(__name__)
    token_data = {}
    stop_event = threading.Event()

    try:
        port = int(redirect_uri.split(":")[-1].split("/")[0])
    except (ValueError, IndexError):
        port = 5000

    @app.route('/')
    def callback():
        if err := request.args.get('error'):
            return f"❌ Authorization Error: {request.args.get('error_description', err)}"
        if code := request.args.get('code'):
            try:
                oauth = OAuth2Session(client_id, scope=scopes, redirect_uri=redirect_uri)
                extra_params = {'access_type': 'offline', 'prompt': 'consent'} if "google.com" in auth_url else {}

                token = oauth.fetch_token(
                    token_url,
                    authorization_response=request.url,
                    client_secret=client_secret,
                    **extra_params
                )
                
                user_email = ""
                if (id_token := token.get('id_token')):
                    try:
                        payload_b64 = id_token.split('.')[1]
                        payload_b64 += '=' * (4 - len(payload_b64) % 4)
                        payload = json.loads(base64.b64decode(payload_b64).decode())
                        user_email = payload.get('email') or payload.get('preferred_username') or payload.get('upn')
                    except Exception:
                        pass
                
                token_data.update({'token': token, 'user_email': user_email})
                
                def delayed_stop():
                    time.sleep(1)
                    stop_event.set()
                threading.Thread(target=delayed_stop, daemon=True).start()
                
                return "✅ Authorization successful! You can close this window and return to the terminal."
            except Exception as e:
                return f"❌ Error fetching token: {e}"
        return "Waiting for authorization code..."

    def run_server():
        from werkzeug.serving import make_server
        server = make_server('127.0.0.1', port, app)
        with app.app_context():
            while not stop_event.is_set():
                server.handle_request()

    threading.Thread(target=run_server, daemon=True).start()

    oauth = OAuth2Session(client_id, scope=scopes, redirect_uri=redirect_uri)
    authorization_url, _ = oauth.authorization_url(auth_url, access_type="offline", prompt="consent")
    
    print(f"\nOpening browser for authorization...")
    print(f"If the browser doesn't open, please visit: {authorization_url}")
    webbrowser.open(authorization_url)

    print("Waiting for callback on local server...")
    stop_event.wait(timeout=120)

    return token_data

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

def setup_scheduling(interval_minutes: int, encryption_password: str | None = None) -> bool:
    """Sets up a periodic sync task using Cron (Unix) or Task Scheduler (Windows)."""
    home = Path.home()
    wugong_dir = home / ".wugong"
    wugong_dir.mkdir(parents=True, exist_ok=True)
    
    # Locate the executable
    wugong_exe = next((p for p in [wugong_dir / "wugong", Path.cwd() / "wugong"] if p.exists()), Path("wugong"))
    log_file = wugong_dir / "sync.log"

    try:
        match platform.system():
            case "Windows":
                # Windows Task Scheduler
                wugong_bat = next((p for p in [wugong_exe.with_suffix(".bat"), Path("wugong.bat")] if p.exists()), Path("wugong.bat"))

                if interval_minutes <= 0:
                    try:
                        subprocess.run(["schtasks", "/delete", "/tn", "WugongSync", "/f"], check=True, capture_output=True)
                        print("✅ Auto-sync disabled (Task Scheduler entry removed).")
                    except subprocess.CalledProcessError:
                        pass
                    return True

                env_prefix = f'set WUGONG_PASSWORD={encryption_password} && ' if encryption_password else ""
                task_command = f'cmd /c "{env_prefix}{wugong_bat} sync all >> \"{log_file}\" 2>&1"'

                cmd = ["schtasks", "/create", "/sc", "minute", "/mo", str(interval_minutes), "/tn", "WugongSync", "/tr", task_command, "/f"]
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"✅ Scheduled sync every {interval_minutes} minutes via Task Scheduler.")
                if encryption_password:
                    print("ℹ️  WUGONG_PASSWORD environment variable included in the scheduled task.")
                print(f"ℹ️  Logs will be saved to: {log_file}")

            case _:
                # Unix-like (macOS/Linux) Cron
                try:
                    current_cron = subprocess.check_output(["crontab", "-l"], stderr=subprocess.STDOUT).decode()
                except subprocess.CalledProcessError:
                    current_cron = ""

                lines = [line for line in current_cron.splitlines() if "wugong sync all" not in line]

                if interval_minutes > 0:
                    env_prefix = f"WUGONG_PASSWORD={encryption_password} " if encryption_password else ""
                    cron_job = f"*/{interval_minutes} * * * * {env_prefix}{wugong_exe} sync all >> {log_file} 2>&1"
                    lines.append(cron_job)
                    print(f"✅ Scheduled sync every {interval_minutes} minutes via Crontab.")
                    if encryption_password:
                        print("ℹ️  WUGONG_PASSWORD environment variable included in the crontab job.")
                    print(f"ℹ️  Logs will be saved to: {log_file}")
                else:
                    print("✅ Auto-sync disabled (Crontab entry removed).")

                new_cron = "\n".join(lines) + "\n"
                process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _, stderr = process.communicate(input=new_cron.encode())

                if process.returncode != 0:
                    print(f"❌ Error setting up crontab: {stderr.decode()}")
                    return False
        return True
    except Exception as e:
        print(f"❌ Failed to setup scheduling: {e}")
        return False

def configure_wizard() -> bool:
    """Allows modifying the sync interval and displays a message about password changes."""
    try:
        print("\n=== Wugong Email Configuration ===")

        config_path = config.get_config_path()
        current_config = config.load_config(config_path)

        if not current_config.get("general", {}).get("salt"):
            print("\n❌ Wugong is not initialized yet. Please run 'wugong init' first.")
            return False

        print("\nℹ️  Master password cannot be modified.")
        print("⚠️  If you need to change your master password, please uninstall and reinstall Wugong.")

        # Logging Setup
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        current_console_level = current_config.get("general", {}).get("console_log_level", "WARNING")
        current_file_level = current_config.get("general", {}).get("file_log_level", "DEBUG")

        if (console_log_level := questionary.select(
            f"Select console log level (current: {current_console_level}):",
            choices=log_levels,
            default=current_console_level
        ).ask()) is None:
            raise KeyboardInterrupt

        if (file_log_level := questionary.select(
            f"Select file log level (current: {current_file_level}):",
            choices=log_levels,
            default=current_file_level
        ).ask()) is None:
            raise KeyboardInterrupt

        # Sync Interval & Scheduling
        current_interval = current_config.get("general", {}).get("sync_interval", 10)
        if (sync_interval := questionary.text(
            f"Sync interval in minutes (current: {current_interval}. Enter 0 to disable auto-sync):",
            default=str(current_interval)
        ).ask()) is None:
            raise KeyboardInterrupt

        interval = int(sync_interval) if sync_interval.isdigit() else current_interval

        if interval != current_interval or console_log_level != current_console_level or file_log_level != current_file_level:
            # Need password if encryption is enabled to update the scheduled task with environment variable
            encryption_password = None
            if current_config.get("general", {}).get("encryption_enabled") or current_config.get("general", {}).get("encrypt_emails"):
                if (encryption_password := config.get_encryption_password(prompt_text="Enter your encryption password to update the scheduled task:")) is None:
                    raise KeyboardInterrupt

            setup_scheduling(interval, encryption_password)
            general = current_config.setdefault("general", {})
            general["sync_interval"] = interval
            general["console_log_level"] = console_log_level
            general["file_log_level"] = file_log_level
            
            config.save_config(current_config, config_path)
            print(f"\n✅ Configuration updated: interval={interval}m, console={console_log_level}, file={file_log_level}.")
        else:
            print("\nNo changes made to configuration.")

        return True
    except KeyboardInterrupt:
        print("\nConfiguration cancelled.")
        return False
    except Exception as e:
        print(f"\n❌ Error during configuration: {e}")
        return False

def init_wizard() -> tuple[bool, str | None]:
    """Initializes the configuration, sets up encryption, and schedules periodic sync."""
    try:
        print("\n=== Wugong Email Initialization ===")

        config_path = config.get_config_path()
        current_config = config.load_config(config_path)

        # Check if already initialized
        if current_config.get("general", {}).get("salt"):
            print("\n❌ Wugong is already initialized.")
            print("⚠️  If you need to change your master password, please uninstall and reinstall Wugong.")
            print("💡 Use 'wugong configure' to modify settings like the sync interval.")
            return False, None

        # 1. Encryption Setup
        if (encrypt_creds := questionary.confirm("Enable credential encryption? (Highly Recommended)", default=True).ask()) is None:
            raise KeyboardInterrupt

        if (encrypt_emails := questionary.confirm("Encrypt locally cached email bodies?", default=True).ask()) is None:
            raise KeyboardInterrupt

        encrypt_enabled = encrypt_creds or encrypt_emails
        encryption_password = None
        salt_val = ""

        if encrypt_enabled:
            print("\n[Mandatory] Since you enabled encryption, a master password is required.")
            if (encryption_password := questionary.password("Set your master encryption password:").ask()) is None:
                raise KeyboardInterrupt
            if not encryption_password:
                print("❌ Master password cannot be empty when encryption is enabled. Initialization aborted.")
                return False, None
            salt_val = base64.b64encode(generate_salt()).decode()
        else:
            print("\n[Warning] Encryption is disabled. Your credentials and data will be stored in plain text.")

        # 2. Logging Setup
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if (console_log_level := questionary.select(
            "Select default console log level:",
            choices=log_levels,
            default="WARNING"
        ).ask()) is None:
            raise KeyboardInterrupt

        if (file_log_level := questionary.select(
            "Select default file log level:",
            choices=log_levels,
            default="DEBUG"
        ).ask()) is None:
            raise KeyboardInterrupt

        # 3. Sync Interval & Scheduling
        if (sync_interval := questionary.text("Sync interval in minutes (e.g., 5, 10, 60. Enter 0 to disable auto-sync):", default="10").ask()) is None:
            raise KeyboardInterrupt

        interval = int(sync_interval) if sync_interval.isdigit() else 10

        if interval > 0:
            setup_scheduling(interval, encryption_password)

        # 4. Save initial config
        general = current_config.setdefault("general", {})
        general["encryption_enabled"] = encrypt_creds
        general["encrypt_emails"] = encrypt_emails
        general["salt"] = salt_val
        general["sync_interval"] = interval
        general["console_log_level"] = console_log_level
        general["file_log_level"] = file_log_level

        config.save_config(current_config, config_path)

        # 5. Success Message
        print(f"\n✅ Configuration initialized and saved to {config_path}")
        print(f"ℹ️  Sync interval: {interval} minutes.")
        print(f"ℹ️  Console log level: {console_log_level}")
        print(f"ℹ️  File log level: {file_log_level} (logged to ~/.wugong/wugong.log)")

        if not current_config.get("accounts"):
            print("\n💡 Tip: No accounts found. Use 'wugong account add' to add your first email account.")

        return True, encryption_password
    except KeyboardInterrupt:
        print("\nInitialization cancelled.")
        return False, None
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        return False, None

def account_add_wizard() -> tuple[list, str | None]:
    newly_added = []
    try:
        print("=== Email Configuration Wizard ===")
        config_path = config.get_config_path()
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)

        first_use = not Path(config_path).exists()
        current_config = config.load_config(config_path)
        original_accounts_count = len(current_config.get('accounts', []))
        if not first_use:
            print(f"Loaded existing config with {original_accounts_count} account(s).")

        encryption_password = None
        if first_use or "salt" not in current_config.get("general", {}):
            print("\nInitialization required.")
            should_continue, encryption_password = init_wizard()
            if not should_continue:
                return [], None
            current_config = config.load_config(config_path)
            
        encrypt_enabled = current_config.get("general", {}).get("encryption_enabled") or current_config.get("general", {}).get("encrypt_emails")
        salt_val = current_config.get("general", {}).get("salt", "")

        if encryption_password is None and encrypt_enabled:
            encryption_password = config.get_encryption_password(prompt_text="Enter your encryption password to add an account:")
            if encryption_password is None:
                raise KeyboardInterrupt

        while True:
            print(f"\n--- Adding Account #{len(current_config.get('accounts', [])) + 1} ---")
            
            has_default = any(acc.get("friendly_name") == "default" for acc in current_config.get("accounts", []))
            is_default = False
            if not has_default:
                if (is_default := questionary.confirm("Set this as your default account? (No friendly name required)").ask()) is None:
                    raise KeyboardInterrupt
            
            friendly_name = "default" if is_default else questionary.text("Friendly Name (e.g., 'Work Gmail'):").ask()
            if friendly_name is None:
                raise KeyboardInterrupt
            if not friendly_name:
                print("Friendly Name is required.")
                continue

            if friendly_name in [acc.get("friendly_name") for acc in current_config.get("accounts", [])]:
                if (overwrite := questionary.confirm(f"Account '{friendly_name}' already exists. Overwrite?").ask()) is None:
                    raise KeyboardInterrupt
                if not overwrite:
                    continue
                current_config["accounts"] = [acc for acc in current_config["accounts"] if acc.get("friendly_name") != friendly_name]
                
            if (provider_name := questionary.select("Select your email provider:", choices=list(EMAIL_PROVIDERS.keys())).ask()) is None:
                raise KeyboardInterrupt
            
            provider_info = EMAIL_PROVIDERS[provider_name]
            if provider_info["hint"]:
                print(f"\n[!] {provider_info['hint']}\n")

            if (login_method := questionary.select("Choose login method:", choices=provider_info["auth_methods"]).ask()) is None:
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

            suggested_imap_port = 993 if imap_tls_method == "SSL/TLS" else 143
            if (imap_port_str := questionary.text("IMAP Port:", default=str(suggested_imap_port)).ask()) is None:
                raise KeyboardInterrupt
            imap_port = int(imap_port_str)
            
            if (smtp_server := questionary.text("SMTP Server:", default=provider_info["smtp_server"]).ask()) is None:
                raise KeyboardInterrupt
            
            if (smtp_tls_method := questionary.select("SMTP TLS Method:", choices=["SSL/TLS", "STARTTLS", "Plain"], default=provider_info.get("smtp_tls_method", "SSL/TLS")).ask()) is None:
                raise KeyboardInterrupt

            match smtp_tls_method:
                case "SSL/TLS": suggested_smtp_port = 465
                case "STARTTLS": suggested_smtp_port = 587
                case _: suggested_smtp_port = 25

            if (smtp_port_str := questionary.text("SMTP Port:", default=str(suggested_smtp_port)).ask()) is None:
                raise KeyboardInterrupt
            smtp_port = int(smtp_port_str)

            auth_details = {}
            password = None
            access_token = ""
            
            match login_method:
                case "Account/Password":
                    pwd_label = "Authorization Code:" if "Authorization Code" in provider_info["hint"] else "Email Password (or App Password):"
                    if (password := questionary.password(pwd_label).ask()) is None:
                        raise KeyboardInterrupt
                    
                    auth_details = {
                        "username": username,
                        "password": encrypt_data(password, encryption_password, salt_val) if encrypt_enabled else password
                    }
                case "OAuth2":
                    if (client_id := questionary.text("OAuth2 Client ID:").ask()) is None or (client_secret := questionary.password("OAuth2 Client Secret:").ask()) is None:
                        raise KeyboardInterrupt
                    
                    auth_url = questionary.text("OAuth2 Authorization URL:", default=provider_info.get("auth_url", "")).ask()
                    token_url = questionary.text("OAuth2 Token URL:", default=provider_info.get("token_url", "")).ask()
                    scopes_input = questionary.text("OAuth2 Scopes (comma separated):", default=",".join(provider_info.get("scopes", []))).ask()
                    redirect_uri = questionary.text("Redirect URI:", default="http://localhost:5000/").ask()
                    
                    if any(v is None for v in [auth_url, token_url, scopes_input, redirect_uri]):
                        raise KeyboardInterrupt
                        
                    scopes = [s.strip() for s in scopes_input.split(",") if s.strip()]
                    if (auto_auth := questionary.confirm("Start local server to automatically fetch tokens?").ask()) is None:
                        raise KeyboardInterrupt
                    
                    refresh_token = ""
                    if auto_auth:
                        if (token_data := start_oauth_flow(client_id, client_secret, auth_url, token_url, scopes, redirect_uri)) and (token := token_data.get('token')):
                            refresh_token = token.get('refresh_token', '')
                            access_token = token.get('access_token', '')
                            if (detected_email := token_data.get('user_email')) and detected_email != username:
                                if (use_detected := questionary.confirm(f"Detected email '{detected_email}' differs from '{username}'. Use detected email?").ask()) is None:
                                    raise KeyboardInterrupt
                                if use_detected:
                                    username = detected_email
                            print(f"\nSuccessfully obtained tokens!")
                        else:
                            print("Failed to obtain tokens automatically. You can enter them manually.")
                    
                    if not refresh_token and (refresh_token := questionary.text("OAuth2 Refresh Token (optional):").ask()) is None:
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
                            "refresh_token": encrypt_data(refresh_token, encryption_password, salt_val) if refresh_token else "",
                            "access_token": encrypt_data(access_token, encryption_password, salt_val) if access_token else ""
                        }
                    else:
                        auth_details = {
                            "username": username, "client_id": client_id, "client_secret": client_secret,
                            "auth_url": auth_url, "token_url": token_url, "redirect_uri": redirect_uri,
                            "scopes": scopes, "refresh_token": refresh_token, "access_token": access_token
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
            
            success, msg = True, ""
            match login_method:
                case "Account/Password":
                    success, msg = test_imap_connection(imap_server, imap_port, username, password=password, tls_method=imap_tls_method)
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

if __name__ == "__main__":
    init_wizard()
