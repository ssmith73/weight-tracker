# init_db.py
import sqlite3
import hashlib
import os

DB_PATH = "weight.db"

def hash_pin(pin: str, salt: bytes = None) -> tuple[str, str]:
    """Generates a secure PBKDF2 hash for a 4-digit PIN using SHA-256."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, 100000)
    return key.hex(), salt.hex()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Expanded Users Table with Height & BMI Threshold
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            pin_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            start_weight REAL DEFAULT 0.0,    -- Stored in kg
            target_weight REAL DEFAULT 0.0,   -- Stored in kg
            target_date TEXT,                 -- ISO format: YYYY-MM-DD
            weekly_rate REAL DEFAULT 0.5,     -- Target loss rate in kg/week
            display_unit TEXT DEFAULT 'lbs',  -- Preferred UI toggle: 'lbs' or 'kg'
            height_cm REAL DEFAULT 0.0,       -- Height in centimeters for BMI calculation
            bmi_threshold REAL DEFAULT 25.0   -- Target BMI threshold line overlay
        );
    """)

    # 2. Weights Table (linked to user)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            weight REAL NOT NULL,             -- Stored in kg
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, date)
        );
    """)

    # 3. Seed default profiles if table is empty
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        print("Initializing default user profiles with goal tracking...")

        # User 1: Sean (PIN: 1234)
        hash1, salt1 = hash_pin("1234")
        cursor.execute("""
            INSERT INTO users (name, pin_hash, salt, start_weight, target_weight, target_date, weekly_rate, display_unit, height_cm, bmi_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Sean", hash1, salt1, 90.7, 81.6, "2027-01-15", 0.68, "lbs", 180.0, 25.0))

        # User 2: Wife (PIN: 5678)
        hash2, salt2 = hash_pin("5678")
        cursor.execute("""
            INSERT INTO users (name, pin_hash, salt, start_weight, target_weight, target_date, weekly_rate, display_unit, height_cm, bmi_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Wife", hash2, salt2, 68.0, 61.2, "2027-02-01", 0.45, "lbs", 165.0, 24.0))

        print("Created default profiles: 'Sean' (PIN: 1234) and 'Wife' (PIN: 5678)")

    conn.commit()
    conn.close()
    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()
