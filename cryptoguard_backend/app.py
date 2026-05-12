import os
import sqlite3
import secrets
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# Flask backend for CryptoGuard.
# This module handles user registration, login/logout, session management,
# transaction recording, and retrieval of transaction history.
# It uses SQLite locally and keeps the API simple for demo/testing.
app = Flask(__name__)
# Allow common local dev servers (Live Server, Vite, etc.). Token is in localStorage, not cookies.
CORS(
    app,
    origins="*",
    allow_headers=["Content-Type", "X-Auth-Token"],
    methods=["GET", "POST", "OPTIONS"],
)

DB_FILE = "transactions.db"

_frontend_override = os.environ.get("CRYPTOGUARD_FRONTEND", "").strip()
FRONTEND_DIR = (
    Path(_frontend_override).resolve()
    if _frontend_override
    else (Path(__file__).resolve().parent.parent / "cryptoguard_frontend")
)

# Open a connection to the SQLite database file.
# The row factory allows query results to be accessed like dictionaries.
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

from contextlib import contextmanager

# Provide a safe context manager for database connections.
# This ensures that the connection is always closed after use.
@contextmanager
def get_db_connection():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


# Create database tables if they do not already exist.
# This runs once at startup and also applies simple schema upgrades.
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


def ensure_guest_user():
    """Create a built-in Guest account for instant demo access (no password needed)."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", ("Guest",))
        if c.fetchone():
            return
        c.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (
                "Guest",
                "guest@cryptoguard.local",
                generate_password_hash(secrets.token_hex(32)),
            ),
        )
        conn.commit()


init_db()
ensure_guest_user()


# Look up the authenticated user from the request token.
# Returns the user_id if the session token is valid.
def get_auth_user_id():
    token = request.headers.get("X-Auth-Token")
    if not token:
        return None
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
        row = c.fetchone()
        return row[0] if row else None


# Retrieve the username for a given user id.
def get_username(user_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row else None


# Endpoint to register a new user. Performs validation and stores a hashed password.
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


# Endpoint to log in an existing user and create a session token.
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


# Instant demo session (same as login but no password).
@app.route("/guest", methods=["POST"])
def guest_login():
    ensure_guest_user()
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", ("Guest",))
        row = c.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Guest account unavailable."}), 500
        user_id = row[0]
    token = secrets.token_hex(32)
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
        conn.commit()
    return jsonify({"ok": True, "token": token, "username": "Guest"})


# Endpoint to log out the current session by deleting the token.
@app.route("/logout", methods=["POST"])
def logout():
    token = request.headers.get("X-Auth-Token")
    if token:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
    return jsonify({"ok": True})


# Endpoint to check whether the user is currently logged in.
@app.route("/me", methods=["GET"])
def me():
    uid = get_auth_user_id()
    if not uid:
        return jsonify({"ok": True, "logged_in": False})
    return jsonify({"ok": True, "logged_in": True, "username": get_username(uid)})


# Endpoint to add a new transaction record for the authenticated user.
# Validates input, prevents past-dated transactions, and checks balance for sells.
@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    # For demo purposes, skip auth and use user_id = 1
    uid = 1
    
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


# Endpoint to return the transaction history for the authenticated user.
@app.route("/transactions")
def get_transactions():
    uid = get_auth_user_id()
    if not uid:
        uid = 1

    with get_db_connection() as conn:
        c = conn.cursor()
        # Get all transactions for the demo user or logged-in user.
        c.execute(
            """
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            """,
            (uid,),
        )
        rows = c.fetchall()
        return jsonify([dict(row) for row in rows])


# Demo endpoint to list all users (for showing database in UI)
@app.route("/all_users")
def all_users():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, username, email FROM users")
        rows = c.fetchall()
        return jsonify([dict(row) for row in rows])


# Demo endpoint to list all transactions (for showing database in UI)
@app.route("/all_transactions")
def all_transactions():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM transactions ORDER BY date DESC")
        rows = c.fetchall()
        return jsonify([dict(row) for row in rows])


# Serve the HTML/CSS/JS so one deployed URL works for login and API (Render, Railway, VPS, etc.).
_API_TOP_NAMES = frozenset(
    {
        "transactions",
        "me",
        "all_users",
        "all_transactions",
        "register",
        "login",
        "guest",
        "logout",
        "add_transaction",
    }
)


@app.route("/")
def serve_index():
    if not FRONTEND_DIR.is_dir():
        return jsonify({"error": "Frontend folder not found.", "path": str(FRONTEND_DIR)}), 503
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def serve_frontend(filename):
    if not FRONTEND_DIR.is_dir():
        return jsonify({"error": "Frontend folder not found.", "path": str(FRONTEND_DIR)}), 503
    if ".." in filename or filename.startswith("/"):
        abort(404)
    top = filename.split("/")[0]
    if top in _API_TOP_NAMES:
        abort(404)
    target = (FRONTEND_DIR / filename).resolve()
    try:
        target.relative_to(FRONTEND_DIR.resolve())
    except ValueError:
        abort(404)
    if not target.is_file():
        abort(404)
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").strip().lower() in ("1", "true", "yes")
    app.run(debug=debug, host="0.0.0.0", port=port)
