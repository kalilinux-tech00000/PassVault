"""
crypto_utils.py — Encryption & Decryption using cryptography (Fernet)
Master password → PBKDF2 key derivation → Fernet symmetric encryption
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


# ── Key Derivation ────────────────────────────────────────────────────────────

def generate_salt() -> str:
    """Generate a random 16-byte salt (hex string for storage)."""
    return os.urandom(16).hex()


def derive_fernet_key(master_password: str, salt_hex: str) -> bytes:
    """
    Derive a 32-byte Fernet key from master password + salt using PBKDF2-HMAC-SHA256.
    Returns URL-safe base64-encoded key (required by Fernet).
    """
    salt = bytes.fromhex(salt_hex)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390_000,          # NIST recommended minimum
        backend=default_backend()
    )
    raw_key = kdf.derive(master_password.encode())
    return base64.urlsafe_b64encode(raw_key)


# ── Password Hashing (for master login) ───────────────────────────────────────

def hash_master_password(password: str, salt_hex: str) -> str:
    """
    Hash the master password using PBKDF2-HMAC-SHA256.
    Returns hex digest for storage.
    """
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt,
        iterations=390_000
    )
    return dk.hex()


def verify_master_password(password: str, salt_hex: str, stored_hash: str) -> bool:
    """Verify a master password against its stored hash."""
    return hash_master_password(password, salt_hex) == stored_hash


# ── Fernet Encrypt / Decrypt ──────────────────────────────────────────────────

def encrypt_password(plaintext: str, fernet_key: bytes) -> str:
    """Encrypt a plaintext password. Returns ciphertext as string."""
    f = Fernet(fernet_key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str, fernet_key: bytes) -> str:
    """Decrypt a ciphertext password. Returns plaintext."""
    f = Fernet(fernet_key)
    return f.decrypt(ciphertext.encode()).decode()
