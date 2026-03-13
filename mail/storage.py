import sqlite3
import os
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
        for em in emails:
            sender = em.get("from", "")
            subject = em.get("subject", "")
            
            if self.encrypt_emails and self.encryption_enabled:
                sender = encrypt_data(sender, password, self.salt)
                subject = encrypt_data(subject, password, self.salt)
            
            cursor.execute('''
                INSERT OR IGNORE INTO emails (account_name, uid, sender, subject, date, seen)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (account_name, em["id"], sender, subject, em["date"], 1 if em.get("seen") else 0))
        conn.commit()
        conn.close()

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
            SELECT uid, sender, subject, date, seen 
            FROM emails WHERE account_name = ? 
            ORDER BY id DESC LIMIT ?
        ''', (account_name, limit))
        rows = cursor.fetchall()
        conn.close()

        email_list = []
        for row in rows:
            uid, sender, subject, date, seen = row
            if self.encrypt_emails and self.encryption_enabled:
                try:
                    sender = decrypt_data(sender, password, self.salt)
                    subject = decrypt_data(subject, password, self.salt)
                except:
                    pass # Or handle error

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
