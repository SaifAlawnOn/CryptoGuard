from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app, origins=['http://127.0.0.1:5500', 'http://localhost:5500'], supports_credentials=True)

DB_FILE = "transactions.db"


def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            coin TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            date TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL
        )
        """
    )
    c.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in c.fetchall()]
    if "email" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN email TEXT")
    c.execute("PRAGMA table_info(transactions)")
    cols = [row[1] for row in c.fetchall()]
    if "user_id" not in cols:
        c.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER")
    conn.commit()
    conn.close()


init_db()


def get_auth_user_id():
    token = request.headers.get("X-Auth-Token")
    if not token:
        return None
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
        row = c.fetchone()
        return row[0] if row else None


def get_username(user_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row else None


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    
    if not username or not email or not password:
        return jsonify({"ok": False, "error": "Username, email, and password are required."}), 400
    if len(username) < 2:
        return jsonify({"ok": False, "error": "Username must be at least 2 characters."}), 400
    if "@" not in email or "." not in email:
        return jsonify({"ok": False, "error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"ok": False, "error": "Password must be at least 6 characters."}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "message": "Registered. You can log in now."}), 201
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return jsonify({"ok": False, "error": "Username already exists"}), 400
        elif "email" in str(e):
            return jsonify({"ok": False, "error": "Email already exists"}), 400
        else:
            return jsonify({"ok": False, "error": "Registration failed."}), 400


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        
    if not row or not check_password_hash(row[1], password):
        return jsonify({"ok": False, "error": "Invalid username or password"}), 401
    
    token = secrets.token_hex(32)
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, row[0]))
        conn.commit()
        
    return jsonify({"ok": True, "token": token, "username": username})


@app.route("/logout", methods=["POST"])
def logout():
    token = request.headers.get("X-Auth-Token")
    if token:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
    return jsonify({"ok": True})


@app.route("/me", methods=["GET"])
def me():
    uid = get_auth_user_id()
    if not uid:
        return jsonify({"ok": True, "logged_in": False})
    return jsonify({"ok": True, "logged_in": True, "username": get_username(uid)})


@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    uid = get_auth_user_id()
    if not uid:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    
    data = request.get_json() or {}
    coin = data.get("coin")
    amount = float(data.get("amount", 0))
    tx_type = data.get("type")
    date = data.get("date")
    
    # Input validation
    if not coin or not tx_type or not date:
        return jsonify({"ok": False, "error": "All fields are required."}), 400
    
    if amount <= 0:
        return jsonify({"ok": False, "error": "Amount must be positive."}), 400
    
    if tx_type not in ["buy", "sell"]:
        return jsonify({"ok": False, "error": "Invalid transaction type."}), 400
    
    # Prevent past date transactions
    try:
        from datetime import datetime, date as date_class
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = date_class.today()
        if selected_date < today:
            return jsonify({"ok": False, "error": "Transactions cannot be made for past dates."}), 400
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid date format."}), 400
    
    # Check sufficient balance for sell transactions
    if tx_type == "sell":
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "SELECT amount, type FROM transactions WHERE user_id = ? AND coin = ?",
            (uid, coin)
        )
        transactions = c.fetchall()
        
        balance = 0
        for tx in transactions:
            tx_amount, tx_type_db = tx
            if tx_type_db == "buy":
                balance += tx_amount
            else:
                balance -= tx_amount
        
        if amount > balance:
            return jsonify({"ok": False, "error": f"Insufficient {coin} balance. You have {balance:.6f} {coin}."}), 400
        
        conn.close()
    
    # Save transaction
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO transactions (coin, amount, type, date, user_id) VALUES (?, ?, ?, ?, ?)",
            (coin, amount, tx_type, date, uid),
        )
        conn.commit()
    return jsonify({"status": "success", "ok": True}), 200


@app.route("/transactions")
def get_transactions():
    uid = get_auth_user_id()
    if not uid:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    
    with get_db_connection() as conn:
        c = conn.cursor()
        # Get all transactions for the user, newest first (by date string YYYY-MM-DD)
        c.execute(
            """
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            """,
            (uid,),
        )
        rows = c.fetchall()
        return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True)
