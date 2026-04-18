from database import get_connection

def add_transaction(coin, amount, ttype, date):

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO transactions
            (coin, amount, type, date)
            VALUES (?, ?, ?, ?)""",
            (coin, amount, ttype, date)
        )

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print("Transaction error:", e)
        return False


def get_transactions():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM transactions")

    data = cursor.fetchall()

    conn.close()

    return data