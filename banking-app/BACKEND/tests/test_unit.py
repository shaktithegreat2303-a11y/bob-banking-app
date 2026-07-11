"""
tests/test_unit.py — Unit tests for auth.py and transactions.py.

Strategy:
  - Each test function creates its own temporary in-memory SQLite database
    via a custom Flask app context so the modules under test behave exactly
    as they do at runtime (using Flask's 'g' object), but without touching
    the real bank.db file.
  - Tests for transactions.py exercise validation branches exhaustively.
  - Tests for auth.py exercise the password verification logic.
"""

import sys
import os
import sqlite3
import pytest

# ---------------------------------------------------------------------------
# Make BACKEND/ importable from any working directory.
# ---------------------------------------------------------------------------
_BACKEND = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from flask import Flask, g
from werkzeug.security import generate_password_hash


# ---------------------------------------------------------------------------
# Helpers — build a minimal in-memory DB and push a Flask app context
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE customers (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT    NOT NULL UNIQUE,
    password TEXT    NOT NULL
);
CREATE TABLE accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL UNIQUE,
    balance     REAL    NOT NULL DEFAULT 0.0,
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);
CREATE TABLE transactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    type       TEXT    NOT NULL,
    amount     REAL    NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);
"""


def _make_app():
    """Return a minimal Flask app configured for testing."""
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True
    return app


def _seed_mem_db(balance=500.0):
    """
    Create an in-memory SQLite DB with one customer + account.
    Returns (connection, customer_id).
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL)
    conn.execute("PRAGMA foreign_keys = ON")

    hashed = generate_password_hash("correctpass")
    cur = conn.execute(
        "INSERT INTO customers (username, password) VALUES (?, ?)",
        ("testuser", hashed),
    )
    customer_id = cur.lastrowid
    conn.execute(
        "INSERT INTO accounts (customer_id, balance) VALUES (?, ?)",
        (customer_id, balance),
    )
    conn.commit()
    return conn, customer_id


# ---------------------------------------------------------------------------
# Auth unit tests
# ---------------------------------------------------------------------------

class TestVerifyLogin:
    """Tests for auth.verify_login()."""

    def test_correct_credentials_return_success(self):
        app = _make_app()
        conn, _ = _seed_mem_db()
        with app.app_context():
            g.db = conn
            from auth import verify_login
            ok, result = verify_login("testuser", "correctpass")
        assert ok is True
        assert result["username"] == "testuser"
        conn.close()

    def test_wrong_password_returns_failure(self):
        app = _make_app()
        conn, _ = _seed_mem_db()
        with app.app_context():
            g.db = conn
            from auth import verify_login
            ok, message = verify_login("testuser", "wrongpass")
        assert ok is False
        assert "Invalid" in message
        conn.close()

    def test_unknown_username_returns_failure(self):
        app = _make_app()
        conn, _ = _seed_mem_db()
        with app.app_context():
            g.db = conn
            from auth import verify_login
            ok, message = verify_login("nobody", "correctpass")
        assert ok is False
        assert "Invalid" in message
        conn.close()

    def test_blank_username_returns_failure(self):
        app = _make_app()
        conn, _ = _seed_mem_db()
        with app.app_context():
            g.db = conn
            from auth import verify_login
            ok, message = verify_login("", "correctpass")
        assert ok is False
        assert "required" in message.lower()
        conn.close()

    def test_blank_password_returns_failure(self):
        app = _make_app()
        conn, _ = _seed_mem_db()
        with app.app_context():
            g.db = conn
            from auth import verify_login
            ok, message = verify_login("testuser", "")
        assert ok is False
        assert "required" in message.lower()
        conn.close()

    def test_same_error_message_for_bad_user_and_bad_pass(self):
        """Security: user enumeration prevention — both failure modes return the same text."""
        app = _make_app()
        conn, _ = _seed_mem_db()
        with app.app_context():
            g.db = conn
            from auth import verify_login
            _, msg_bad_user = verify_login("nobody", "x")
            _, msg_bad_pass = verify_login("testuser", "wrongpass")
        assert msg_bad_user == msg_bad_pass
        conn.close()


# ---------------------------------------------------------------------------
# Transaction unit tests
# ---------------------------------------------------------------------------

class TestDeposit:
    """Tests for transactions.process_deposit()."""

    def _run(self, customer_id, raw_amount, conn):
        app = _make_app()
        with app.app_context():
            g.db = conn
            from transactions import process_deposit
            return process_deposit(customer_id, raw_amount)

    def test_valid_deposit_succeeds(self):
        conn, cid = _seed_mem_db(balance=500.0)
        ok, msg = self._run(cid, "100", conn)
        assert ok is True
        row = conn.execute("SELECT balance FROM accounts WHERE customer_id=?", (cid,)).fetchone()
        assert row["balance"] == pytest.approx(600.0)
        conn.close()

    def test_zero_amount_fails(self):
        conn, cid = _seed_mem_db()
        ok, msg = self._run(cid, "0", conn)
        assert ok is False
        assert "greater than zero" in msg.lower()
        conn.close()

    def test_negative_amount_fails(self):
        conn, cid = _seed_mem_db()
        ok, msg = self._run(cid, "-50", conn)
        assert ok is False
        assert "greater than zero" in msg.lower()
        conn.close()

    def test_non_numeric_amount_fails(self):
        conn, cid = _seed_mem_db()
        ok, msg = self._run(cid, "abc", conn)
        assert ok is False
        assert "valid number" in msg.lower()
        conn.close()

    def test_decimal_deposit_recorded_correctly(self):
        conn, cid = _seed_mem_db(balance=0.0)
        ok, _ = self._run(cid, "49.99", conn)
        assert ok is True
        row = conn.execute("SELECT balance FROM accounts WHERE customer_id=?", (cid,)).fetchone()
        assert row["balance"] == pytest.approx(49.99)
        conn.close()

    def test_transaction_ledger_entry_created(self):
        conn, cid = _seed_mem_db()
        acc = conn.execute("SELECT id FROM accounts WHERE customer_id=?", (cid,)).fetchone()
        self._run(cid, "75", conn)
        tx = conn.execute("SELECT * FROM transactions WHERE account_id=?", (acc["id"],)).fetchone()
        assert tx is not None
        assert tx["type"] == "deposit"
        assert tx["amount"] == pytest.approx(75.0)
        conn.close()


class TestWithdrawal:
    """Tests for transactions.process_withdrawal()."""

    def _run(self, customer_id, raw_amount, conn):
        app = _make_app()
        with app.app_context():
            g.db = conn
            from transactions import process_withdrawal
            return process_withdrawal(customer_id, raw_amount)

    def test_valid_withdrawal_succeeds(self):
        conn, cid = _seed_mem_db(balance=300.0)
        ok, msg = self._run(cid, "100", conn)
        assert ok is True
        row = conn.execute("SELECT balance FROM accounts WHERE customer_id=?", (cid,)).fetchone()
        assert row["balance"] == pytest.approx(200.0)
        conn.close()

    def test_withdrawal_exceeding_balance_fails(self):
        conn, cid = _seed_mem_db(balance=100.0)
        ok, msg = self._run(cid, "200", conn)
        assert ok is False
        assert "insufficient" in msg.lower()
        conn.close()

    def test_exact_balance_withdrawal_succeeds(self):
        conn, cid = _seed_mem_db(balance=100.0)
        ok, _ = self._run(cid, "100", conn)
        assert ok is True
        row = conn.execute("SELECT balance FROM accounts WHERE customer_id=?", (cid,)).fetchone()
        assert row["balance"] == pytest.approx(0.0)
        conn.close()

    def test_zero_amount_fails(self):
        conn, cid = _seed_mem_db()
        ok, msg = self._run(cid, "0", conn)
        assert ok is False
        assert "greater than zero" in msg.lower()
        conn.close()

    def test_negative_amount_fails(self):
        conn, cid = _seed_mem_db()
        ok, msg = self._run(cid, "-10", conn)
        assert ok is False
        assert "greater than zero" in msg.lower()
        conn.close()

    def test_non_numeric_amount_fails(self):
        conn, cid = _seed_mem_db()
        ok, msg = self._run(cid, "xyz", conn)
        assert ok is False
        assert "valid number" in msg.lower()
        conn.close()

    def test_balance_unchanged_on_failed_withdrawal(self):
        conn, cid = _seed_mem_db(balance=50.0)
        self._run(cid, "999", conn)
        row = conn.execute("SELECT balance FROM accounts WHERE customer_id=?", (cid,)).fetchone()
        assert row["balance"] == pytest.approx(50.0)
        conn.close()

    def test_transaction_ledger_entry_created(self):
        conn, cid = _seed_mem_db(balance=200.0)
        acc = conn.execute("SELECT id FROM accounts WHERE customer_id=?", (cid,)).fetchone()
        self._run(cid, "50", conn)
        tx = conn.execute("SELECT * FROM transactions WHERE account_id=?", (acc["id"],)).fetchone()
        assert tx is not None
        assert tx["type"] == "withdrawal"
        assert tx["amount"] == pytest.approx(50.0)
        conn.close()
