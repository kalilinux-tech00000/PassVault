"""
vault.py — CRUD operations for stored web credentials
All passwords stored Fernet-encrypted; decrypted only when requested.
"""

from database import get_connection
from crypto_utils import encrypt_password, decrypt_password


# ── Add ───────────────────────────────────────────────────────────────────────

def add_credential(site_name: str, site_url: str, username: str,
                   plaintext_password: str, fernet_key: bytes, notes: str = "") -> int:
    """Encrypt and store a new web credential. Returns new record ID."""
    encrypted = encrypt_password(plaintext_password, fernet_key)
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO passwords (site_name, site_url, username, encrypted_password, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (site_name, site_url, username, encrypted, notes)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    print(f"[VAULT] Credential for '{site_name}' saved (ID={new_id}).")
    return new_id


# ── List ──────────────────────────────────────────────────────────────────────

def list_credentials() -> list:
    """Return all credentials (passwords remain encrypted)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, site_name, site_url, username, notes, created_at, updated_at FROM passwords ORDER BY site_name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Get / Decrypt ─────────────────────────────────────────────────────────────

def get_credential(record_id: int, fernet_key: bytes) -> dict | None:
    """Fetch and decrypt a single credential by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM passwords WHERE id = ?", (record_id,)
    ).fetchone()
    conn.close()

    if not row:
        print(f"[VAULT] No record found with ID={record_id}.")
        return None

    result = dict(row)
    result["decrypted_password"] = decrypt_password(result["encrypted_password"], fernet_key)
    return result


# ── Search ────────────────────────────────────────────────────────────────────

def search_credentials(keyword: str) -> list:
    """Search by site name or URL (no decryption needed)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, site_name, site_url, username, notes, created_at
        FROM passwords
        WHERE site_name LIKE ? OR site_url LIKE ? OR username LIKE ?
        ORDER BY site_name
        """,
        (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Update ────────────────────────────────────────────────────────────────────

def update_credential(record_id: int, fernet_key: bytes,
                      new_password: str = None, new_notes: str = None) -> bool:
    """Update password and/or notes for an existing credential."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM passwords WHERE id = ?", (record_id,)).fetchone()
    if not row:
        conn.close()
        return False

    encrypted = encrypt_password(new_password, fernet_key) if new_password else row["encrypted_password"]
    notes = new_notes if new_notes is not None else row["notes"]

    conn.execute(
        """
        UPDATE passwords
        SET encrypted_password = ?, notes = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (encrypted, notes, record_id)
    )
    conn.commit()
    conn.close()
    print(f"[VAULT] Credential ID={record_id} updated.")
    return True


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_credential(record_id: int) -> bool:
    """Delete a credential by ID."""
    conn = get_connection()
    cursor = conn.execute("DELETE FROM passwords WHERE id = ?", (record_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    if deleted:
        print(f"[VAULT] Credential ID={record_id} deleted.")
    else:
        print(f"[VAULT] No record found with ID={record_id}.")
    return deleted
