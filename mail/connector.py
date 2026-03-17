import imaplib
import smtplib
import base64
import socket
from typing import Any, Callable, Optional
from logger import setup_logger

logger = setup_logger("connector")

class MailConnector:
    def __init__(
        self, 
        auth_manager: Any, 
        config: dict[str, Any], 
        save_config_callback: Callable[[], None],
        non_interactive: bool = False
    ) -> None:
        self.auth_manager = auth_manager
        self.config = config
        self.save_config_callback = save_config_callback
        self.non_interactive = non_interactive

    def get_imap_connection(self, account: dict[str, Any], auth_password: str, timeout: int = 60) -> imaplib.IMAP4:
        """Connects and authenticates to IMAP server."""
        imap_server: str = account['imap_server']
        imap_port: int = int(account['imap_port'])
        tls_method: str = account.get('imap_tls_method', 'SSL/TLS')
        
        logger.debug(f"Connecting to IMAP {imap_server}:{imap_port} using {tls_method}")
        
        mail = self._create_imap_client(imap_server, imap_port, tls_method, timeout)
        auth = self.auth_manager.decrypt_account_auth(account, auth_password)
        
        try:
            mail = self._authenticate_imap(mail, account, auth, auth_password, timeout)
        except Exception as e:
            try:
                mail.logout()
            except:
                pass
            raise e

        self._setup_utf8_accept(mail)
        return mail

    def get_smtp_connection(self, account: dict[str, Any], auth_password: str, timeout: int = 30) -> smtplib.SMTP:
        """Connects and authenticates to SMTP server."""
        smtp_server: str = account['smtp_server']
        smtp_port: int = int(account['smtp_port'])
        tls_method: str = account.get('smtp_tls_method', 'SSL/TLS' if smtp_port == 465 else ('STARTTLS' if smtp_port == 587 else 'Plain'))
        
        logger.debug(f"Connecting to SMTP {smtp_server}:{smtp_port} using {tls_method}")
        
        server = self._create_smtp_client(smtp_server, smtp_port, tls_method, timeout)
        auth = self.auth_manager.decrypt_account_auth(account, auth_password)
        
        try:
            self._authenticate_smtp(server, account, auth, auth_password)
        except Exception as e:
            try:
                server.quit()
            except:
                pass
            raise e

        return server

    def _create_imap_client(self, server: str, port: int, tls_method: str, timeout: int) -> imaplib.IMAP4:
        match tls_method:
            case "SSL/TLS":
                return imaplib.IMAP4_SSL(server, port, timeout=timeout)
            case "STARTTLS":
                mail = imaplib.IMAP4(server, port, timeout=timeout)
                mail.starttls()
                return mail
            case _:
                return imaplib.IMAP4(server, port, timeout=timeout)

    def _create_smtp_client(self, server: str, port: int, tls_method: str, timeout: int) -> smtplib.SMTP:
        match tls_method:
            case "SSL/TLS":
                return smtplib.SMTP_SSL(server, port, timeout=timeout)
            case _:
                smtp = smtplib.SMTP(server, port, timeout=timeout)
                smtp.ehlo()
                if tls_method == "STARTTLS" and smtp.has_extn('STARTTLS'):
                    smtp.starttls()
                    smtp.ehlo()
                return smtp

    def _authenticate_imap(self, mail: imaplib.IMAP4, account: dict[str, Any], auth: dict[str, Any], auth_password: str, timeout: int) -> imaplib.IMAP4:
        login_method = account['login_method']
        user = auth.get("username")
        
        match login_method:
            case "Password":
                mail.login(user, auth['password'])
                logger.info(f"IMAP: Logged in as {user} using password")
                return mail
            case _:
                token = auth.get("access_token")
                try:
                    res, data = mail.authenticate('XOAUTH2', lambda x: f"user={user}\x01auth=Bearer {token}\x01\x01".encode())
                    if res == "OK":
                        logger.info(f"IMAP: Logged in as {user} using OAuth2")
                        return mail
                except imaplib.IMAP4.error as e:
                    if "auth" in str(e).lower() or "expired" in str(e).lower():
                        logger.info("IMAP OAuth2 token expired, refreshing...")
                        new_auth = self.auth_manager.refresh_oauth2_token(account, auth_password)
                        if new_auth:
                            # Update config with new tokens (or cleared tokens)
                            account['auth'] = new_auth
                            self.save_config_callback()
                            
                            if new_token_encrypted := new_auth.get('access_token'):
                                # Decrypt new token for use
                                new_token = self.auth_manager.decrypt_account_auth(account, auth_password)['access_token']
                                
                                res, data = mail.authenticate('XOAUTH2', lambda x: f"user={user}\x01auth=Bearer {new_token}\x01\x01".encode())
                                if res == "OK":
                                     logger.info(f"IMAP: Logged in as {user} using refreshed OAuth2")
                                     return mail
                                     
                            # If refresh failed (returned empty tokens) or new token still fails, try full re-auth
                            logger.info("Refreshing failed, attempting full re-authorization...")
                            new_auth = self.auth_manager.reauthorize_oauth2(account, auth_password, non_interactive=self.non_interactive)
                            if new_auth and (new_token_encrypted := new_auth.get('access_token')):
                                account['auth'] = new_auth
                                self.save_config_callback()
                                new_token = self.auth_manager.decrypt_account_auth(account, auth_password)['access_token']
                                res, data = mail.authenticate('XOAUTH2', lambda x: f"user={user}\x01auth=Bearer {new_token}\x01\x01".encode())
                                if res == "OK":
                                    logger.info(f"IMAP: Logged in as {user} using re-authorized OAuth2")
                                    return mail
                        raise e
        return mail

    def _authenticate_smtp(self, server: smtplib.SMTP, account: dict[str, Any], auth: dict[str, Any], auth_password: str) -> None:
        login_method = account['login_method']
        user = auth.get("username")
        
        match login_method:
            case "Password":
                server.login(user, auth['password'])
                logger.info(f"SMTP: Logged in as {user} using password")
            case _:
                token = auth.get("access_token")
                auth_str = f"user={user}\x01auth=Bearer {token}\x01\x01"
                try:
                    server.docmd("AUTH", "XOAUTH2 " + base64.b64encode(auth_str.encode()).decode())
                except smtplib.SMTPResponseException as e:
                    if e.smtp_code == 535: # Auth failed / expired
                        logger.info("SMTP OAuth2 token expired, refreshing...")
                        new_auth = self.auth_manager.refresh_oauth2_token(account, auth_password)
                        if new_auth:
                            # Update config with new tokens (or cleared tokens)
                            account['auth'] = new_auth
                            self.save_config_callback()
                            
                            if new_token_encrypted := new_auth.get('access_token'):
                                # Decrypt new token for use
                                new_token = self.auth_manager.decrypt_account_auth(account, auth_password)['access_token']
                                
                                new_auth_str = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                                server.docmd("AUTH", "XOAUTH2 " + base64.b64encode(new_auth_str.encode()).decode())
                                logger.info(f"SMTP: Logged in as {user} using refreshed OAuth2")
                                return
                                
                        # If refresh failed (returned empty tokens) or new token still fails, try full re-auth
                        logger.info("SMTP: Refreshing failed, attempting full re-authorization...")
                        new_auth = self.auth_manager.reauthorize_oauth2(account, auth_password, non_interactive=self.non_interactive)
                        if new_auth and (new_token_encrypted := new_auth.get('access_token')):
                            account['auth'] = new_auth
                            self.save_config_callback()
                            new_token = self.auth_manager.decrypt_account_auth(account, auth_password)['access_token']
                            new_auth_str = f"user={user}\x01auth=Bearer {new_token}\x01\x01"
                            server.docmd("AUTH", "XOAUTH2 " + base64.b64encode(new_auth_str.encode()).decode())
                            logger.info(f"SMTP: Logged in as {user} using re-authorized OAuth2")
                            return
                        raise e
                    else:
                        raise e

    def _setup_utf8_accept(self, mail: imaplib.IMAP4) -> None:
        """Enable UTF8=ACCEPT if supported by server."""
        try:
            res_cap, cap_data = mail.capability()
            if res_cap == "OK":
                caps = str(cap_data).upper()
                if "UTF8=ACCEPT" in caps:
                    res, data = mail._simple_command("ENABLE", "UTF8=ACCEPT")
                    if res == "OK":
                        mail._utf8_enabled = True
                        logger.debug("IMAP: UTF8=ACCEPT enabled")
        except Exception as e:
            logger.debug(f"IMAP: Failed to enable UTF8=ACCEPT: {e}")
