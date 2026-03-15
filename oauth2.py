import base64
import json
import time
import threading
import webbrowser
import logging
import os
from flask import Flask, request
from requests_oauthlib import OAuth2Session

# Disable Flask/Werkzeug default logs to keep terminal clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Allow insecure transport for local testing if needed (though usually https is required by providers)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Relax scope matching for providers like Microsoft that might return different scopes than requested
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

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
