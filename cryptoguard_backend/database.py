import sqlite3

DB_NAME = "cryptoguard.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wallet(
        wallet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_name TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        coin TEXT,
        amount REAL,
        type TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()