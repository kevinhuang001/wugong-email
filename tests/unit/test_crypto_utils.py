import pytest
import os
from crypto_utils import encrypt_data, decrypt_data, generate_salt, derive_key

def test_encrypt_decrypt_roundtrip():
    password = "secret_password"
    salt = generate_salt()
    original_text = "Hello, World! 🌍"
    
    encrypted = encrypt_data(original_text, password, salt)
    assert encrypted != original_text
    
    decrypted = decrypt_data(encrypted, password, salt)
    assert decrypted == original_text

def test_decrypt_wrong_password():
    password = "correct_password"
    wrong_password = "wrong_password"
    salt = generate_salt()
    original_text = "Sensitive data"
    
    encrypted = encrypt_data(original_text, password, salt)
    
    with pytest.raises(Exception):
        decrypt_data(encrypted, wrong_password, salt)

def test_derive_key_consistency():
    password = "pwd"
    salt = b"constant_salt"
    key1 = derive_key(password, salt)
    key2 = derive_key(password, salt)
    assert key1 == key2

def test_derive_key_different_salt():
    password = "pwd"
    key1 = derive_key(password, b"salt1")
    key2 = derive_key(password, b"salt2")
    assert key1 != key2
