import base64
import json
import time
import threading
import webbrowser
import logging
import os
from rich.console import Console
from rich.panel import Panel
from flask import Flask, request
from requests_oauthlib import OAuth2Session

# Disable Flask/Werkzeug default logs to keep terminal clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Allow insecure transport for local testing if needed (though usually https is required by providers)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Relax scope matching for providers like Microsoft that might return different scopes than requested
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

logger = logging.getLogger("wugong.oauth2")

def start_oauth_flow(client_id: str, client_secret: str, auth_url: str, token_url: str, scopes: list[str], redirect_uri: str) -> dict:
    """Starts a local server to handle OAuth2 callback and returns the token."""
    app = Flask(__name__)
    token_data = {}
    stop_event = threading.Event()
    server = None

    try:
        # Extract host and port from redirect_uri
        host = redirect_uri.split("://")[1].split(":")[0]
        try:
            port = int(redirect_uri.split(":")[-1].split("/")[0])
        except (ValueError, IndexError):
            port = 80 if redirect_uri.startswith("http://") else 443
    except Exception:
        host = '127.0.0.1'
        port = 5000

    @app.route('/')
    def callback():
        def delayed_shutdown():
            time.sleep(2)  # Give browser time to receive and render the response
            if server:
                server.shutdown()

        if "error" in request.args:
            err = request.args.get("error")
            error_desc = request.args.get("error_description", err)
            logger.error(f"❌ Authorization Error: {err} - {error_desc}")
            threading.Thread(target=delayed_shutdown).start()
            return f"<h2>❌ Authorization Error</h2><p>{error_desc}</p><p>Please return to the terminal and try again.</p>"
            
        if "code" in request.args:
            try:
                oauth = OAuth2Session(client_id, scope=scopes, redirect_uri=redirect_uri)
                extra_params = {'access_type': 'offline', 'prompt': 'consent'} if "google.com" in auth_url else {}

                token = oauth.fetch_token(
                    token_url,
                    authorization_response=request.url,
                    client_id=client_id,
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
                
                threading.Thread(target=delayed_shutdown).start()
                return "<h2>✅ Authorization successful!</h2><p>You can close this window and return to the terminal.</p><script>setTimeout(()=>window.close(), 3000);</script>"
            except Exception as e:
                logger.error(f"❌ Error fetching token: {e}")
                threading.Thread(target=delayed_shutdown).start()
                return f"<h2>❌ Error fetching token</h2><p>Details: {e}</p><p>Please return to the terminal and try again.</p>"
        
        # Initial visit if not code/error
        oauth = OAuth2Session(client_id, scope=scopes, redirect_uri=redirect_uri)
        authorization_url, _ = oauth.authorization_url(auth_url, access_type="offline", prompt="consent")
        return f'<h2>Authorization Required</h2><p>If you were not automatically redirected, <a href="{authorization_url}">please click here to login</a> with your Microsoft account.</p>'

    def run_server():
        nonlocal server
        from werkzeug.serving import make_server
        try:
            server = make_server(host, port, app)
            server.serve_forever()
        except OSError as e:
            if e.errno in [98, 48]: # Address already in use
                logger.error(f"❌ Port conflict: Port {port} is already in use!")
                logger.error(f"👉 Solution: Change the port in your REDIRECT_URI (e.g., to 5002) and update it in your provider's dashboard.")
            else:
                logger.error(f"❌ Failed to start local auth server: {e}")
        finally:
            stop_event.set()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give server a moment to start
    time.sleep(1)
    if stop_event.is_set():
        return {}

    oauth = OAuth2Session(client_id, scope=scopes, redirect_uri=redirect_uri)
    authorization_url, _ = oauth.authorization_url(auth_url, access_type="offline", prompt="consent")
    
    console = Console()
    console.print(Panel(
        f"[bold blue]🚀 OAuth2 Authorization Required[/bold blue]\n\n"
        f"If your browser didn't open automatically, please visit this URL:\n\n"
        f"[cyan]{authorization_url}[/cyan]\n\n"
        f"[yellow]⏳ Waiting for you to complete the login in your browser...[/yellow]",
        title="Wugong Email Login",
        expand=False
    ))
    
    webbrowser.open(authorization_url)

    logger.info("⏳ Waiting for callback on local server (timeout 600s)...")
    if not stop_event.wait(timeout=600):
        logger.warning("⚠️ Authorization timed out after 10 minutes.")
    
    if server:
        server.shutdown()

    return token_data
