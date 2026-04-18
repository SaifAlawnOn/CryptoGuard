import sqlite3
from database import get_connection

def create_wallet(name):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO wallet(wallet_name) VALUES(?)",
            (name,)
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print("Wallet creation error:", e)