import os
import base64
import toml
import questionary
import threading
import webbrowser
import logging
import config
from flask import Flask, request
from requests_oauthlib import OAuth2Session
from crypto_utils import generate_salt, encrypt_data

# Disable Flask/Werkzeug default logs to keep terminal clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Allow insecure transport for local testing if needed (though usually https is required by providers)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Relax scope matching for providers like Microsoft that might return different scopes than requested
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

CONFIG_FILE = "config.toml"

EMAIL_PROVIDERS = {
    "Gmail": {
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 465,
        "auth_methods": ["OAuth2", "Account/Password"],
        "auth_url": "https://accounts.google.com/o/oauth2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://mail.google.com/"],
        "hint": "Note: Gmail requires an 'App Password' if using Account/Password and 2FA is enabled."
    },
    "Outlook": {
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
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
        "smtp_server": "smtp.qq.com",
        "smtp_port": 465,
        "auth_methods": ["Account/Password"],
        "auth_url": "",
        "token_url": "",
        "scopes": [],
        "hint": "Note: QQ Mail REQUIRES an 'Authorization Code' (授权码) instead of your regular password."
    },
    "163 Mail": {
        "imap_server": "imap.163.com",
        "imap_port": 993,
        "smtp_server": "smtp.163.com",
        "smtp_port": 465,
        "auth_methods": ["Account/Password"],
        "auth_url": "",
        "token_url": "",
        "scopes": [],
        "hint": "Note: 163 Mail REQUIRES an 'Authorization Code' (授权码) instead of your regular password."
    },
    "Other": {
        "imap_server": "",
        "imap_port": 993,
        "smtp_server": "",
        "smtp_port": 465,
        "auth_methods": ["Account/Password", "OAuth2"],
        "auth_url": "",
        "token_url": "",
        "scopes": [],
        "hint": ""
    }
}

def start_oauth_flow(client_id, client_secret, auth_url, token_url, scopes, redirect_uri):
    """Starts a local server to handle OAuth2 callback and returns the token."""
    app = Flask(__name__)
    token_data = {}
    stop_event = threading.Event()

    # Determine port from redirect_uri
    try:
        port = int(redirect_uri.split(":")[-1].split("/")[0])
    except:
        port = 5000 # Default

    @app.route('/')
    def callback():
        if "error" in request.args:
            return f"❌ Authorization Error: {request.args.get('error_description', request.args.get('error', 'Unknown error'))}"
        if "code" in request.args:
            try:
                oauth = OAuth2Session(client_id, scope=scopes, redirect_uri=redirect_uri)
                # For Gmail, we need to specify access_type='offline' to get refresh_token
                extra_params = {}
                if "google.com" in auth_url:
                    extra_params['access_type'] = 'offline'
                    extra_params['prompt'] = 'consent'

                token = oauth.fetch_token(
                    token_url,
                    authorization_response=request.url,
                    client_secret=client_secret,
                    **extra_params
                )
                
                # --- DEBUG LOGGING START ---
                print("\n[DEBUG] OAuth2 Token Keys:", list(token.keys()))
                # --- DEBUG LOGGING END ---
                
                # Attempt to extract email from id_token or other fields
                user_email = ""
                if 'id_token' in token:
                    import json
                    # id_token is a JWT (header.payload.signature)
                    try:
                        payload_b64 = token['id_token'].split('.')[1]
                        # Fix padding
                        payload_b64 += '=' * (4 - len(payload_b64) % 4)
                        payload = json.loads(base64.b64decode(payload_b64).decode())
                        
                        # --- DEBUG LOGGING START ---
                        print("[DEBUG] ID Token Payload:", json.dumps(payload, indent=2))
                        # --- DEBUG LOGGING END ---
                        
                        user_email = payload.get('email') or payload.get('preferred_username') or payload.get('upn')
                    except Exception as e:
                        print(f"[DEBUG] Error decoding ID Token: {e}")
                        pass
                
                token_data['token'] = token
                token_data['user_email'] = user_email
                
                # Use a small delay before stopping the server to allow the browser to receive the response
                def delayed_stop():
                    import time
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
        ctx = app.app_context()
        ctx.push()
        while not stop_event.is_set():
            server.handle_request()

    # Start server in a background thread
    threading.Thread(target=run_server, daemon=True).start()

    # Open browser
    oauth = OAuth2Session(client_id, scope=scopes, redirect_uri=redirect_uri)
    authorization_url, state = oauth.authorization_url(auth_url, access_type="offline", prompt="consent")
    
    print(f"\nOpening browser for authorization...")
    print(f"If the browser doesn't open, please visit: {authorization_url}")
    webbrowser.open(authorization_url)

    # Wait for token
    print("Waiting for callback on local server...")
    stop_event.wait(timeout=120) # 2 minute timeout

    return token_data

def run_wizard():
    try:
        print("=== Email Configuration Wizard ===")
        
        # Determine config path using centralized config module
        config_path = config.get_config_path()
        
        # Ensure directory exists
        config_dir = os.path.dirname(config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        # 1. Load existing config or initialize new one
        first_use = not os.path.exists(config_path)
        current_config = config.load_config(config_path)
        original_accounts_count = len(current_config.get('accounts', []))
        
        if not first_use:
            print(f"Loaded existing config with {original_accounts_count} account(s).")

        # 2. Setup/Verify encryption
        if first_use:
            print("First use detected. Please set up global encryption settings.")
            
            encryption_password = questionary.password("Set an encryption password for sensitive data (accounts, tokens):").ask()
            if encryption_password is None: raise KeyboardInterrupt
            if not encryption_password:
                print("Password cannot be empty.")
                return
                
            encrypt_emails = questionary.confirm("Encrypt locally stored emails?").ask()
            if encrypt_emails is None: raise KeyboardInterrupt
            
            encrypt_enabled = questionary.confirm("Enable encryption for account credentials?").ask()
            if encrypt_enabled is None: raise KeyboardInterrupt
            
            salt_val = generate_salt()
            current_config["general"]["encryption_enabled"] = encrypt_enabled
            current_config["general"]["encrypt_emails"] = encrypt_emails
            current_config["general"]["salt"] = base64.b64encode(salt_val).decode() if encrypt_enabled else ""
        else:
            encryption_password = questionary.password("Enter your encryption password to proceed:").ask()
            if encryption_password is None: raise KeyboardInterrupt
            
            # Simple validation: Try to decrypt one piece of sensitive data if it exists
            if current_config.get("accounts"):
                first_acc = current_config["accounts"][0]
                first_auth = first_acc.get("auth", {})
                sensitive_keys = ["password", "client_id", "client_secret", "refresh_token", "access_token"]
                
                test_val = None
                for k in sensitive_keys:
                    if first_auth.get(k):
                        test_val = first_auth[k]
                        break
                
                if test_val:
                    from crypto_utils import decrypt_data
                    from rich import print as rprint
                    try:
                        decrypt_data(test_val, encryption_password, config.get_salt(current_config))
                    except Exception:
                        rprint("[red]Error: Incorrect encryption password. Access denied.[/red]")
                        return
            
            encrypt_enabled = current_config["general"]["encryption_enabled"]
            encrypt_emails = current_config["general"].get("encrypt_emails", False)
            salt_val = config.get_salt(current_config)

        # 3. Add Account(s) Loop
        while True:
            print(f"\n--- Adding Account #{len(current_config['accounts']) + 1} ---")
            
            is_default = False
            # Check if a default account already exists
            has_default = any(acc.get("friendly_name") == "default" for acc in current_config["accounts"])
            
            if not has_default:
                is_default = questionary.confirm("Set this as your default account? (No friendly name required)").ask()
                if is_default is None: raise KeyboardInterrupt
            
            if is_default:
                friendly_name = "default"
            else:
                friendly_name = questionary.text("Friendly Name (e.g., 'Work Gmail'):").ask()
                if friendly_name is None: raise KeyboardInterrupt
                if not friendly_name:
                    print("Friendly Name is required.")
                    continue

            # Check if friendly name already exists
            existing_names = [acc.get("friendly_name") for acc in current_config.get("accounts", [])]
            if friendly_name in existing_names:
                overwrite = questionary.confirm(f"Account '{friendly_name}' already exists. Overwrite?").ask()
                if overwrite is None: raise KeyboardInterrupt
                if not overwrite:
                    continue
                # Remove existing account for overwrite
                current_config["accounts"] = [acc for acc in current_config["accounts"] if acc.get("friendly_name") != friendly_name]
                
            provider_name = questionary.select(
                "Select your email provider:",
                choices=list(EMAIL_PROVIDERS.keys())
            ).ask()
            if provider_name is None: raise KeyboardInterrupt
            
            provider_info = EMAIL_PROVIDERS[provider_name]
            if provider_info["hint"]:
                print(f"\n[!] {provider_info['hint']}\n")

            login_method = questionary.select(
                "Choose login method:",
                choices=provider_info["auth_methods"]
            ).ask()
            if login_method is None: raise KeyboardInterrupt

            # 1. Ask for Email Account (Username) first for both methods
            username = questionary.text("Email Account (e.g. yourname@example.com):").ask()
            if username is None: raise KeyboardInterrupt
            if not username:
                print("Email Account is required.")
                continue

            imap_server = questionary.text("IMAP Server:", default=provider_info["imap_server"]).ask()
            if imap_server is None: raise KeyboardInterrupt
            
            imap_port_str = questionary.text("IMAP Port:", default=str(provider_info["imap_port"])).ask()
            if imap_port_str is None: raise KeyboardInterrupt
            imap_port = int(imap_port_str)
            
            smtp_server = questionary.text("SMTP Server:", default=provider_info["smtp_server"]).ask()
            if smtp_server is None: raise KeyboardInterrupt
            
            smtp_port_str = questionary.text("SMTP Port:", default=str(provider_info["smtp_port"])).ask()
            if smtp_port_str is None: raise KeyboardInterrupt
            smtp_port = int(smtp_port_str)

            auth_details = {}
            if login_method == "Account/Password":
                pwd_label = "Authorization Code (授权码):" if "授权码" in provider_info["hint"] else "Email Password (or App Password):"
                password = questionary.password(pwd_label).ask()
                if password is None: raise KeyboardInterrupt
                
                if encrypt_enabled:
                    auth_details = {
                        "username": username,
                        "password": encrypt_data(password, encryption_password, salt_val)
                    }
                else:
                    auth_details = {"username": username, "password": password}
            else:
                # OAuth2 details
                client_id = questionary.text("OAuth2 Client ID:").ask()
                if client_id is None: raise KeyboardInterrupt
                
                client_secret = questionary.password("OAuth2 Client Secret:").ask()
                if client_secret is None: raise KeyboardInterrupt
                
                auth_url = questionary.text("OAuth2 Authorization URL:", default=provider_info.get("auth_url", "")).ask()
                if auth_url is None: raise KeyboardInterrupt
                
                token_url = questionary.text("OAuth2 Token URL:", default=provider_info.get("token_url", "")).ask()
                if token_url is None: raise KeyboardInterrupt
                
                scopes_input = questionary.text("OAuth2 Scopes (comma separated):", default=",".join(provider_info.get("scopes", []))).ask()
                if scopes_input is None: raise KeyboardInterrupt
                scopes = [s.strip() for s in scopes_input.split(",") if s.strip()]
                
                redirect_uri = questionary.text("Redirect URI:", default="http://localhost:5000/").ask()
                if redirect_uri is None: raise KeyboardInterrupt
                
                auto_auth = questionary.confirm("Start local server to automatically fetch tokens?").ask()
                if auto_auth is None: raise KeyboardInterrupt
                
                refresh_token = ""
                access_token = ""
                
                if auto_auth:
                    token_data = start_oauth_flow(client_id, client_secret, auth_url, token_url, scopes, redirect_uri)
                    if token_data and 'token' in token_data:
                        token = token_data['token']
                        refresh_token = token.get('refresh_token', '')
                        access_token = token.get('access_token', '')
                        # If token_data has an email, update the username
                        detected_email = token_data.get('user_email', '')
                        if detected_email and detected_email != username:
                            use_detected = questionary.confirm(f"Detected email '{detected_email}' differs from '{username}'. Use detected email?").ask()
                            if use_detected is None: raise KeyboardInterrupt
                            if use_detected:
                                username = detected_email
                        
                        print(f"\nSuccessfully obtained tokens!")
                    else:
                        print("Failed to obtain tokens automatically. You can enter them manually.")
                
                if not refresh_token:
                    refresh_token = questionary.text("OAuth2 Refresh Token (optional):").ask()
                    if refresh_token is None: raise KeyboardInterrupt
                
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
                        "username": username,
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_url": auth_url,
                        "token_url": token_url,
                        "redirect_uri": redirect_uri,
                        "scopes": scopes,
                        "refresh_token": refresh_token,
                        "access_token": access_token
                    }

            # Create account object
            account = {
                "friendly_name": friendly_name,
                "login_method": login_method,
                "imap_server": imap_server,
                "imap_port": imap_port,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "auth": auth_details
            }
            
            current_config["accounts"].append(account)
            
            add_another = questionary.confirm("Add another account?").ask()
            if add_another is None: raise KeyboardInterrupt
            if not add_another:
                break

        # 4. Save to config.toml
        config.save_config(current_config, config_path)

        print(f"\nConfiguration saved to {config_path} with {len(current_config['accounts'])} account(s)!")

    except KeyboardInterrupt:
        new_accounts_count = len(current_config.get("accounts", [])) - original_accounts_count
        if new_accounts_count > 0:
            # If there are new accounts added, save them
            config.save_config(current_config, config_path)
            print(f"\n[!] Configuration interrupted. {new_accounts_count} new account(s) were saved to {config_path}.")
        else:
            print("\n[!] Configuration cancelled. No changes were made.")
        return

if __name__ == "__main__":
    run_wizard()
