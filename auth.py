"""
auth.py — Master user registration & login with audit logging
"""

import socket
from database import get_connection
from crypto_utils import (
    generate_salt,
    hash_master_password,
    verify_master_password,
    derive_fernet_key,
)


def get_local_ip() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


# ── Login Log ─────────────────────────────────────────────────────────────────

def log_login(username: str, status: str, reason: str = None):
    """Write a login attempt to login_logs table."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO login_logs (username, status, ip_address, reason)
        VALUES (?, ?, ?, ?)
        """,
        (username, status, get_local_ip(), reason)
    )
    conn.commit()
    conn.close()


# ── Registration ──────────────────────────────────────────────────────────────

def register_master_user(username: str, master_password: str) -> bool:
    """
    Register the master user. Only one master account allowed.
    Returns True on success, False if already exists.
    """
    conn = get_connection()
    existing = conn.execute("SELECT id FROM master_user LIMIT 1").fetchone()
    if existing:
        conn.close()
        print("[AUTH] Master user already exists. Cannot register again.")
        return False

    salt = generate_salt()
    pw_hash = hash_master_password(master_password, salt)
    conn.execute(
        "INSERT INTO master_user (username, password_hash, salt) VALUES (?, ?, ?)",
        (username, pw_hash, salt)
    )
    conn.commit()
    conn.close()
    print(f"[AUTH] Master user '{username}' registered successfully.")
    return True


# ── Login ─────────────────────────────────────────────────────────────────────

def login(username: str, master_password: str):
    """
    Authenticate master user.
    Returns Fernet key (bytes) on success, None on failure.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM master_user WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if not row:
        log_login(username, "FAILED", "User not found")
        print("[AUTH] Login failed: user not found.")
        return None

    if not verify_master_password(master_password, row["salt"], row["password_hash"]):
        log_login(username, "FAILED", "Wrong password")
        print("[AUTH] Login failed: incorrect password.")
        return None

    log_login(username, "SUCCESS")
    fernet_key = derive_fernet_key(master_password, row["salt"])
    print(f"[AUTH] Login successful. Welcome, {username}!")
    return fernet_key
