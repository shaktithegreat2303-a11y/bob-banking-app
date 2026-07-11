"""
db.py — Database connection helper and data-access functions.

Responsibilities:
  - Open and configure an SQLite connection per request (dict-like rows).
  - Create the three tables (customers, accounts, transactions) on first run.
  - Seed one demo customer with a hashed password and a starting balance.
  - Provide helper query functions consumed by auth.py and transactions.py.
"""

import sqlite3
import os
from flask import g
from werkzeug.security import generate_password_hash

# Resolve the absolute path to bank.db regardless of the working directory.
_DB_PATH = os.path.join(os.path.dirname(__file__), "bank.db")

# ---------------------------------------------------------------------------
# Connection management (per-request via Flask's 'g' object)
# ---------------------------------------------------------------------------

def get_db():
    """Return the database connection for the current request, opening it if necessary."""
    if "db" not in g:
        g.db = sqlite3.connect(_DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row   # rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    """Close the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT    NOT NULL UNIQUE,
    password TEXT    NOT NULL        -- bcrypt-style hash via werkzeug
);

CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL UNIQUE,
    balance     REAL    NOT NULL DEFAULT 0.0,
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id  INTEGER NOT NULL,
    type        TEXT    NOT NULL,   -- 'deposit' or 'withdrawal'
    amount      REAL    NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);
"""


def init_db(app):
    """Create all tables and seed the demo customer. Called once at app startup."""
    with app.app_context():
        db = sqlite3.connect(_DB_PATH)
        db.row_factory = sqlite3.Row
        db.executescript(_DDL)
        db.commit()
        _seed(db)
        db.close()


def _seed(db):
    """Insert a demo customer and account if none exist yet."""
    existing = db.execute("SELECT id FROM customers LIMIT 1").fetchone()
    if existing:
        return  # already seeded

    hashed_pw = generate_password_hash("password123")
    cur = db.execute(
        "INSERT INTO customers (username, password) VALUES (?, ?)",
        ("demo_user", hashed_pw),
    )
    customer_id = cur.lastrowid
    db.execute(
        "INSERT INTO accounts (customer_id, balance) VALUES (?, ?)",
        (customer_id, 1000.00),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_customer_by_username(db, username):
    """Return the customer row for *username*, or None if not found."""
    return db.execute(
        "SELECT * FROM customers WHERE username = ?", (username,)
    ).fetchone()


def get_account_by_customer_id(db, customer_id):
    """Return the account row for *customer_id*, or None if not found."""
    return db.execute(
        "SELECT * FROM accounts WHERE customer_id = ?", (customer_id,)
    ).fetchone()


def update_balance(db, account_id, new_balance):
    """Overwrite the balance for *account_id* and commit."""
    db.execute(
        "UPDATE accounts SET balance = ? WHERE id = ?",
        (new_balance, account_id),
    )
    db.commit()


def record_transaction(db, account_id, tx_type, amount):
    """Insert a ledger row for *account_id* and commit."""
    db.execute(
        "INSERT INTO transactions (account_id, type, amount) VALUES (?, ?, ?)",
        (account_id, tx_type, amount),
    )
    db.commit()
