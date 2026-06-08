"""
database.py — SQLite setup for Password Manager
Tables: master_user, passwords, login_logs
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "password_manager.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Master user table (one master account)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,   -- bcrypt hash of master password
            salt TEXT NOT NULL,            -- salt used for key derivation
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Stored web credentials
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT NOT NULL,
            site_url TEXT,
            username TEXT NOT NULL,
            encrypted_password TEXT NOT NULL,   -- Fernet encrypted
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Login audit log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            status TEXT NOT NULL,           -- 'SUCCESS' or 'FAILED'
            ip_address TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            reason TEXT                     -- failure reason if any
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")
