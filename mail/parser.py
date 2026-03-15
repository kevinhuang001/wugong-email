import email
from email.header import decode_header, make_header
from email.utils import parseaddr
from typing import Any, List, Optional, Dict
from .storage_manager import Email

class MailParser:
    """Handles all email parsing and metadata extraction logic."""
    
    @staticmethod
    def decode_header(header_val: str | None, default: str) -> str:
        """Robustly decode email headers."""
        if not header_val:
            return default
        try:
            return str(make_header(decode_header(header_val)))
        except Exception:
            return header_val or default

    @classmethod
    def parse_basic_metadata(cls, uid_str: str, msg: email.message.Message, resp_text: str, folder: str) -> Dict[str, Any]:
        """Extract basic metadata from email headers (for listing)."""
        subject = cls.decode_header(msg.get("Subject"), "No Subject")
        from_header = cls.decode_header(msg.get("From"), "Unknown")
        name, email_addr = parseaddr(from_header)
        
        return {
            "id": uid_str,
            "folder": folder,
            "from": name or from_header,
            "from_email": email_addr,
            "subject": subject,
            "date": msg.get("Date"),
            "seen": '\\Seen' in resp_text
        }

    @classmethod
    def parse_full_email(cls, account_name: str, uid_str: str, msg: email.message.Message, status_data: str, folder: str) -> Email:
        """Parse full email content and attachments into Email dataclass."""
        subject = cls.decode_header(msg.get("Subject"), "No Subject")
        from_header = cls.decode_header(msg.get("From"), "Unknown")
        name, email_addr = parseaddr(from_header)
        
        content = ""
        html_content = ""
        attachments: List[str] = []
        
        if msg.is_multipart():
            for part in msg.walk():
                c_type = part.get_content_type()
                c_disp = str(part.get("Content-Disposition"))
                
                if "attachment" in c_disp:
                    if filename := part.get_filename():
                        attachments.append(cls.decode_header(filename, "unnamed"))
                    continue

                if not (payload := part.get_payload(decode=True)):
                    continue
                
                charset = part.get_content_charset() or "utf-8"
                if c_type == "text/plain":
                    try: content = payload.decode(charset, errors="replace")
                    except: content = payload.decode("utf-8", errors="replace")
                elif c_type == "text/html":
                    try: html_content = payload.decode(charset, errors="replace")
                    except: html_content = payload.decode("utf-8", errors="replace")
        else:
            c_type = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            if payload := msg.get_payload(decode=True):
                if c_type == "text/html":
                    try: html_content = payload.decode(charset, errors="replace")
                    except: html_content = payload.decode("utf-8", errors="replace")
                else:
                    try: content = payload.decode(charset, errors="replace")
                    except: content = payload.decode("utf-8", errors="replace")
        
        return Email(
            account_name=account_name,
            folder=folder,
            uid=uid_str,
            sender=name or from_header,
            sender_email=email_addr,
            subject=subject,
            date=msg.get("Date") or "",
            seen='\\Seen' in str(status_data),
            content=content or html_content,
            content_type="text/plain" if content else "html_only",
            attachments=attachments
        )
