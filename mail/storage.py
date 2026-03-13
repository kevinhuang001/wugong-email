import sqlite3
import os
from datetime import datetime
from crypto_utils import decrypt_data, encrypt_data

class StorageManager:
    def __init__(self, db_path, encrypt_emails, encryption_enabled, salt):
        self.db_path = db_path
        self.encrypt_emails = encrypt_emails
        self.encryption_enabled = encryption_enabled
        self.salt = salt
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT,
                uid TEXT,
                sender TEXT,
                sender_email TEXT,
                subject TEXT,
                date TEXT,
                seen INTEGER,
                content_type TEXT,
                content TEXT,
                UNIQUE(account_name, uid)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_status (
                account_name TEXT PRIMARY KEY,
                last_sync_time TEXT,
                last_uid TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT,
                action_type TEXT, -- e.g., 'delete'
                uid TEXT,
                created_at TEXT
            )
        ''')

        # Check if sender_email column exists (for older databases)
        cursor.execute("PRAGMA table_info(emails)")
        columns = [column[1] for column in cursor.fetchall()]
        if "sender_email" not in columns:
            cursor.execute("ALTER TABLE emails ADD COLUMN sender_email TEXT")
            
        conn.commit()
        conn.close()

    def get_last_sync_info(self, account_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT last_sync_time, last_uid FROM sync_status WHERE account_name = ?", (account_name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"time": row[0], "uid": row[1]}
        return {"time": "Never", "uid": "0"}

    def update_sync_info(self, account_name, last_sync_time, last_uid):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO sync_status (account_name, last_sync_time, last_uid)
            VALUES (?, ?, ?)
        ''', (account_name, last_sync_time, last_uid))
        conn.commit()
        conn.close()

    def save_emails_to_cache(self, account_name, emails, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        new_uids = []
        for em in emails:
            uid = em["id"]
            sender = em.get("from", "")
            sender_email = em.get("from_email", "")
            subject = em.get("subject", "")
            
            if self.encrypt_emails and self.encryption_enabled:
                sender = encrypt_data(sender, password, self.salt)
                sender_email = encrypt_data(sender_email, password, self.salt)
                subject = encrypt_data(subject, password, self.salt)
            
            # Check if this UID already exists for this account
            cursor.execute("SELECT 1 FROM emails WHERE account_name = ? AND uid = ?", (account_name, uid))
            if not cursor.fetchone():
                new_uids.append(uid)

            cursor.execute('''
                INSERT INTO emails (account_name, uid, sender, sender_email, subject, date, seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_name, uid) DO UPDATE SET
                    sender = excluded.sender,
                    sender_email = excluded.sender_email,
                    subject = excluded.subject,
                    date = excluded.date,
                    seen = excluded.seen
            ''', (account_name, uid, sender, sender_email, subject, em["date"], 1 if em.get("seen") else 0))
        conn.commit()
        conn.close()
        return new_uids

    def update_email_content(self, account_name, uid, content_type, content, password):
        if self.encrypt_emails and self.encryption_enabled:
            content = encrypt_data(content, password, self.salt)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE emails SET content_type = ?, content = ?, seen = 1 
            WHERE account_name = ? AND uid = ?
        ''', (content_type, content, account_name, uid))
        conn.commit()
        conn.close()

    def get_emails_from_cache(self, account_name, limit, search_criteria, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT uid, sender, sender_email, subject, date, seen 
            FROM emails WHERE account_name = ? 
            ORDER BY id DESC LIMIT ?
        ''', (account_name, limit))
        rows = cursor.fetchall()
        conn.close()

        email_list = []
        for row in rows:
            uid, sender, sender_email, subject, date, seen = row
            if self.encrypt_emails and self.encryption_enabled:
                # Decrypt each field individually and safely
                # Helper to decrypt and return original if fails
                def safe_decrypt(val):
                    if not val: return val
                    # Check if it looks like Fernet encrypted data (starts with gAAAAAB)
                    if isinstance(val, str) and val.startswith("gAAAAAB"):
                        try:
                            return decrypt_data(val, password, self.salt)
                        except Exception:
                            return f"[Decryption Failed] {val[:10]}..."
                    return val

                sender = safe_decrypt(sender)
                sender_email = safe_decrypt(sender_email)
                subject = safe_decrypt(subject)

            # Basic fuzzy search/filtering in memory if search_criteria provided
            if search_criteria:
                # Use str() to ensure we don't call lower() on None, 
                # or use (val or "") pattern which is safer.
                keyword = str(search_criteria.get("keyword") or "").lower()
                from_filter = str(search_criteria.get("from") or "").lower()
                
                subject_lower = str(subject or "").lower()
                sender_lower = str(sender or "").lower()
                
                if keyword and (keyword not in subject_lower and keyword not in sender_lower):
                    continue
                if from_filter and from_filter not in sender_lower:
                    continue

            email_list.append({
                "id": uid,
                "from": sender,
                "from_email": sender_email,
                "subject": subject,
                "date": date,
                "seen": bool(seen)
            })
        return email_list

    def get_email_content(self, account_name, uid, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content_type, content FROM emails WHERE account_name = ? AND uid = ?", (account_name, uid))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[1]:
            content_type, content = row
            if self.encrypt_emails and self.encryption_enabled:
                content = decrypt_data(content, password, self.salt)
            return content_type, content
        return None, None

    def delete_email_from_cache(self, account_name, uid):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emails WHERE account_name = ? AND uid = ?", (account_name, uid))
        conn.commit()
        conn.close()

    def update_email_seen_status(self, account_name, uid, seen):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE emails SET seen = ? 
            WHERE account_name = ? AND uid = ?
        ''', (1 if seen else 0, account_name, uid))
        conn.commit()
        conn.close()

    def get_all_cached_uids(self, account_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT uid FROM emails WHERE account_name = ?", (account_name,))
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def add_pending_action(self, account_name, action_type, uid):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pending_actions (account_name, action_type, uid, created_at)
            VALUES (?, ?, ?, ?)
        ''', (account_name, action_type, uid, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    def get_pending_actions(self, account_name, action_type=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if action_type:
            cursor.execute("SELECT id, uid FROM pending_actions WHERE account_name = ? AND action_type = ?", (account_name, action_type))
        else:
            cursor.execute("SELECT id, action_type, uid FROM pending_actions WHERE account_name = ?", (account_name,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def remove_pending_action(self, action_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_actions WHERE id = ?", (action_id,))
        conn.commit()
        conn.close()
