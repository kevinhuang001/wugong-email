from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Generator
from dataclasses import dataclass
from contextlib import contextmanager
import sqlite3
import json
from crypto_utils import decrypt_data, encrypt_data
from logger import logger

@dataclass
class Email:
    account_name: str
    folder: str
    uid: str
    sender: str
    sender_email: str
    subject: str
    date: str
    seen: bool
    content_type: str
    content: str
    attachments: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.uid,
            "folder": self.folder,
            "from": self.sender,
            "from_email": self.sender_email,
            "subject": self.subject,
            "date": self.date,
            "seen": self.seen,
            "content_type": self.content_type,
            "content": self.content,
            "attachments": self.attachments
        }

class MailStorageManager:
    def __init__(self, db_path: str | Path, encrypt_emails: bool, encryption_enabled: bool, salt: str):
        self.db_path = Path(db_path)
        self.encrypt_emails = encrypt_emails
        self.encryption_enabled = encryption_enabled
        self.salt = salt
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for SQLite connections."""
        with sqlite3.connect(self.db_path) as conn:
            yield conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_name TEXT,
                    folder TEXT DEFAULT 'INBOX',
                    uid TEXT,
                    sender TEXT,
                    sender_email TEXT,
                    subject TEXT,
                    date TEXT,
                    seen INTEGER,
                    content_type TEXT,
                    content TEXT,
                    attachments TEXT,
                    UNIQUE(account_name, folder, uid)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_status (
                    account_name TEXT,
                    folder TEXT DEFAULT 'INBOX',
                    last_sync_time TEXT,
                    last_uid TEXT,
                    PRIMARY KEY (account_name, folder)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_name TEXT,
                    action_type TEXT,
                    uid TEXT,
                    folder TEXT DEFAULT 'INBOX',
                    created_at TEXT
                )
            ''')

            # Handle migrations
            cursor.execute("PRAGMA table_info(emails)")
            columns = {column[1] for column in cursor.fetchall()}
            
            if "folder" not in columns:
                cursor.execute("ALTER TABLE emails ADD COLUMN folder TEXT DEFAULT 'INBOX'")
                logger.info("Added folder column to emails table.")
            
            if "sender_email" not in columns:
                cursor.execute("ALTER TABLE emails ADD COLUMN sender_email TEXT")
                logger.info("Added sender_email column to emails table.")
            
            if "attachments" not in columns:
                cursor.execute("ALTER TABLE emails ADD COLUMN attachments TEXT")
                logger.info("Added attachments column to emails table.")
            
            # Update pending_actions table if it doesn't have folder column
            cursor.execute("PRAGMA table_info(pending_actions)")
            pending_columns = {column[1] for column in cursor.fetchall()}
            if "folder" not in pending_columns:
                cursor.execute("ALTER TABLE pending_actions ADD COLUMN folder TEXT DEFAULT 'INBOX'")
                logger.info("Added folder column to pending_actions table.")
            
            # Update sync_status table if it doesn't have folder column
            cursor.execute("PRAGMA table_info(sync_status)")
            sync_columns = {column[1] for column in cursor.fetchall()}
            if "folder" not in sync_columns:
                # Migration for sync_status is trickier because it's a PRIMARY KEY change.
                # Simplest way: drop and recreate since it's just sync metadata.
                cursor.execute("DROP TABLE sync_status")
                cursor.execute('''
                    CREATE TABLE sync_status (
                        account_name TEXT,
                        folder TEXT DEFAULT 'INBOX',
                        last_sync_time TEXT,
                        last_uid TEXT,
                        PRIMARY KEY (account_name, folder)
                    )
                ''')
                logger.info("Recreated sync_status table with folder support.")

            conn.commit()

    def get_last_sync_info(self, account_name: str, folder: str = "INBOX") -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_sync_time, last_uid FROM sync_status WHERE account_name = ? AND folder = ?", (account_name, folder))
            return {"time": row[0], "uid": row[1]} if (row := cursor.fetchone()) else {"time": "Never", "uid": "0"}

    def update_sync_info(self, account_name: str, folder: str, last_sync_time: str, last_uid: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO sync_status (account_name, folder, last_sync_time, last_uid)
                VALUES (?, ?, ?, ?)
            ''', (account_name, folder, last_sync_time, last_uid))
            conn.commit()

    def _safe_encrypt(self, val: str, password: str) -> str:
        return encrypt_data(val, password, self.salt) if val and self.encrypt_emails and self.encryption_enabled else val

    def _safe_decrypt(self, val: str, password: str) -> str:
        if not val or not (self.encrypt_emails and self.encryption_enabled):
            return val
        if isinstance(val, str) and val.startswith("gAAAAAB"):
            try:
                return decrypt_data(val, password, self.salt)
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                return "[Decryption Failed]"
        return val

    def save_emails_to_cache(self, account_name: str, folder: str, emails: List[Dict[str, Any]], password: str) -> List[str]:
        new_uids = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for em in emails:
                uid = em["id"]
                sender = self._safe_encrypt(em.get("from", ""), password)
                sender_email = self._safe_encrypt(em.get("from_email", ""), password)
                subject = self._safe_encrypt(em.get("subject", ""), password)
                content = self._safe_encrypt(em.get("content", ""), password)
                
                attachments_json = json.dumps(em.get("attachments", [])) if em.get("attachments") else ""
                attachments = self._safe_encrypt(attachments_json, password)
                
                cursor.execute("SELECT 1 FROM emails WHERE account_name = ? AND folder = ? AND uid = ?", (account_name, folder, uid))
                if not cursor.fetchone():
                    new_uids.append(uid)

                cursor.execute('''
                    INSERT INTO emails (account_name, folder, uid, sender, sender_email, subject, date, seen, content_type, content, attachments)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(account_name, folder, uid) DO UPDATE SET
                        sender = excluded.sender,
                        sender_email = excluded.sender_email,
                        subject = excluded.subject,
                        date = excluded.date,
                        seen = excluded.seen,
                        content_type = CASE WHEN excluded.content_type != '' THEN excluded.content_type ELSE emails.content_type END,
                        content = CASE WHEN excluded.content != '' THEN excluded.content ELSE emails.content END,
                        attachments = CASE WHEN excluded.attachments != '' THEN excluded.attachments ELSE emails.attachments END
                ''', (account_name, folder, uid, sender, sender_email, subject, em["date"], 1 if em.get("seen") else 0, em.get("content_type", ""), content, attachments))
            conn.commit()
        return new_uids

    def get_emails_from_cache(
        self, 
        account_name: str, 
        limit: int, 
        search_criteria: Optional[Dict[str, Any]], 
        password: str,
        folder: Optional[str] = None,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT uid, folder, sender, sender_email, subject, date, seen, content_type, content FROM emails WHERE account_name = ?"
            params = [account_name]
            
            if folder:
                query += " AND folder = ?"
                params.append(folder)
            
            # Mapping sort fields
            field_map = {
                "date": "date",
                "subject": "subject",
                "from": "sender",
                "uid": "uid"
            }
            db_field = field_map.get(sort_by, "date")
            order = "DESC" if sort_order.lower() == "desc" else "ASC"
            
            # If encryption is enabled and we're sorting by an encrypted field (subject or sender),
            # we MUST sort in Python after decryption.
            is_encrypted_sort = (self.encrypt_emails and self.encryption_enabled and db_field in ["subject", "sender"])
            
            if not is_encrypted_sort:
                query += f" ORDER BY {db_field} {order}"
            
            # If we're searching OR sorting by an encrypted field, we fetch all rows and handle in Python.
            if not search_criteria and not is_encrypted_sort:
                if limit != -1:
                    query += " LIMIT ?"
                    params.append(limit)
                cursor.execute(query, params)
            else:
                cursor.execute(query, params)
                
            rows = cursor.fetchall()

        email_list = []
        for row in rows:
            uid, row_folder, sender_enc, sender_email_enc, subject_enc, date, seen, content_type, content_enc = row

            sender = self._safe_decrypt(sender_enc, password)
            sender_email = self._safe_decrypt(sender_email_enc, password)
            subject = self._safe_decrypt(subject_enc, password)
            content = self._safe_decrypt(content_enc, password) if content_enc else None

            if search_criteria:
                keyword = str(search_criteria.get("keyword") or "").lower()
                from_filter = str(search_criteria.get("from") or "").lower()
                
                match_found = True
                if keyword:
                    match_found = any(keyword in str(f or "").lower() for f in [subject, sender, sender_email, content])
                
                if match_found and from_filter:
                    match_found = from_filter in str(sender or "").lower() or from_filter in str(sender_email or "").lower()
                
                if not match_found:
                    continue

            email_list.append({
                "id": uid, 
                "folder": row_folder,
                "from": sender, 
                "from_email": sender_email, 
                "subject": subject, 
                "date": date, 
                "seen": bool(seen)
            })
            
            # If we used SQL LIMIT, we don't need to break here (but it doesn't hurt)
            if not search_criteria and not is_encrypted_sort and limit != -1 and len(email_list) >= limit:
                break
        
        # Handle Python-side sorting if needed
        if is_encrypted_sort:
            reverse = (order == "DESC")
            sort_key_map = {
                "subject": lambda x: x["subject"].lower(),
                "sender": lambda x: x["from"].lower()
            }
            email_list.sort(key=sort_key_map.get(db_field, lambda x: x["date"]), reverse=reverse)
            
            # Apply limit after sorting
            if limit != -1:
                email_list = email_list[:limit]
        elif search_criteria:
            # If we were searching, we also need to apply limit here because we fetched all
            if limit != -1:
                email_list = email_list[:limit]
                
        return email_list

    def get_email_full_details(self, account_name: str, uid: str, password: str, folder: str = "INBOX") -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sender, sender_email, subject, date, content_type, content, attachments 
                FROM emails WHERE account_name = ? AND uid = ? AND folder = ?
            ''', (account_name, uid, folder))
            if not (row := cursor.fetchone()):
                return None
            
        sender_enc, sender_email_enc, subject_enc, date, content_type, content_enc, attachments_enc = row
        
        attachments_json = self._safe_decrypt(attachments_enc, password)
        try:
            attachments_list = json.loads(attachments_json) if attachments_json else []
        except (json.JSONDecodeError, TypeError):
            attachments_list = [attachments_json] if attachments_json else []
        
        return {
            "from": self._safe_decrypt(sender_enc, password),
            "from_email": self._safe_decrypt(sender_email_enc, password),
            "subject": self._safe_decrypt(subject_enc, password),
            "date": date,
            "content_type": content_type,
            "content": self._safe_decrypt(content_enc, password),
            "attachments": attachments_list,
            "folder": folder
        }

    def get_email_count(self, account_name: str, folder: Optional[str] = None, only_unseen: bool = False) -> int:
        """Get the number of cached emails for an account (optionally filtered by folder or seen status)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) FROM emails WHERE account_name = ?"
            params = [account_name]
            
            if folder:
                query += " AND folder = ?"
                params.append(folder)
            
            if only_unseen:
                query += " AND seen = 0"
                
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def get_all_cached_uids(self, account_name: str, folder: str = "INBOX") -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uid FROM emails WHERE account_name = ? AND folder = ?", (account_name, folder))
            return [row[0] for row in cursor.fetchall()]

    def delete_email_from_cache(self, account_name: str, uid: str, folder: str = "INBOX") -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM emails WHERE account_name = ? AND uid = ? AND folder = ?", (account_name, uid, folder))

    def update_seen_status(self, account_name: str, uid: str, seen: bool, folder: str = "INBOX") -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE emails SET seen = ? WHERE account_name = ? AND uid = ? AND folder = ?", (1 if seen else 0, account_name, uid, folder))

    def add_pending_action(self, account_name: str, action_type: str, uid: str, folder: str = "INBOX") -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO pending_actions (account_name, action_type, uid, folder, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (account_name, action_type, uid, folder, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    def get_pending_actions(self, account_name: str, action_type: Optional[str] = None) -> List[Tuple]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if action_type:
                cursor.execute("SELECT id, uid, folder FROM pending_actions WHERE account_name = ? AND action_type = ?", (account_name, action_type))
            else:
                cursor.execute("SELECT id, action_type, uid, folder FROM pending_actions WHERE account_name = ?", (account_name,))
            return cursor.fetchall()

    def remove_pending_action(self, action_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM pending_actions WHERE id = ?", (action_id,))

    def get_cached_statuses(self, account_name: str, uids: List[str], folder: str = "INBOX") -> Dict[str, bool]:
        if not uids:
            return {}
        
        results = {}
        batch_size = 900
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for i in range(0, len(uids), batch_size):
                batch = uids[i:i + batch_size]
                placeholders = ",".join(["?"] * len(batch))
                cursor.execute(f"SELECT uid, seen FROM emails WHERE account_name = ? AND folder = ? AND uid IN ({placeholders})", (account_name, folder, *batch))
                for uid, seen in cursor.fetchall():
                    results[uid] = bool(seen)
        return results
