import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a 32-byte key from a password and salt using PBKDF2."""
    # Use fewer iterations for tests to speed them up
    iterations = 1000 if os.environ.get("WUGONG_TESTING") == "1" else 100000
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_data(data: str, password: str, salt: bytes) -> str:
    """Encrypts a string using a password and salt."""
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str, password: str, salt: bytes) -> str:
    """Decrypts a string using a password and salt."""
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.decrypt(encrypted_data.encode()).decode()

def generate_salt() -> bytes:
    """Generates a random 16-byte salt."""
    return os.urandom(16)

def is_fernet_token(data: str) -> bool:
    """Check if a string looks like a Fernet-encrypted token."""
    if not isinstance(data, str) or not data:
        return False
    # Fernet tokens always start with 'gAAAAA' (base64 for version 0x80)
    # and they should be base64-decodable.
    if not data.startswith("gAAAAA"):
        return False
    try:
        base64.urlsafe_b64decode(data.encode())
        return True
    except Exception:
        return False
