"""
tests/test_integration.py — Integration tests for Flask routes.

Strategy:
  - Configure app.py with a temporary in-memory SQLite database so every
    test run starts fresh and never touches the real bank.db file.
  - Use Flask's built-in test client to issue simulated HTTP requests.
  - Verify HTTP status codes, redirect targets, flash messages, and
    balance state after each operation.
"""

import sys
import os
import sqlite3
import pytest

# ---------------------------------------------------------------------------
# Path setup — make BACKEND/ importable.
# ---------------------------------------------------------------------------
_BACKEND = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


# ---------------------------------------------------------------------------
# Fixture — build a fresh test application and seed it once per test.
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT    NOT NULL UNIQUE,
    password TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL UNIQUE,
    balance     REAL    NOT NULL DEFAULT 0.0,
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);
CREATE TABLE IF NOT EXISTS transactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    type       TEXT    NOT NULL,
    amount     REAL    NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);
"""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """
    Yield a Flask test client backed by a temporary SQLite file.
    The monkeypatch swaps db._DB_PATH so no real bank.db is created.
    """
    from werkzeug.security import generate_password_hash
    import db as db_module

    # Point the db module at a temp file for this test.
    test_db_path = str(tmp_path / "test_bank.db")
    monkeypatch.setattr(db_module, "_DB_PATH", test_db_path)

    # Seed the temp database directly (bypassing init_db which needs app context).
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL)
    conn.execute("PRAGMA foreign_keys = ON")
    hashed = generate_password_hash("password123")
    cur = conn.execute(
        "INSERT INTO customers (username, password) VALUES (?, ?)",
        ("testuser", hashed),
    )
    cid = cur.lastrowid
    conn.execute(
        "INSERT INTO accounts (customer_id, balance) VALUES (?, ?)",
        (cid, 1000.0),
    )
    conn.commit()
    conn.close()

    # Import app *after* monkeypatching so it picks up the new DB path.
    import importlib
    import app as app_module
    importlib.reload(app_module)

    app_module.app.config["TESTING"] = True
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    app_module.app.secret_key = "integration-test-secret"

    with app_module.app.test_client() as c:
        yield c


def _login(client, username="testuser", password="password123"):
    """Helper: POST to /login and follow the redirect."""
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# Authentication route tests
# ---------------------------------------------------------------------------

class TestLoginRoute:

    def test_login_page_renders(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"Customer Login" in resp.data

    def test_valid_login_redirects_to_dashboard(self, client):
        resp = _login(client)
        assert resp.status_code == 200
        assert b"Current Balance" in resp.data

    def test_wrong_password_stays_on_login_with_error(self, client):
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "wrongpass"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Invalid" in resp.data

    def test_unknown_user_stays_on_login_with_error(self, client):
        resp = client.post(
            "/login",
            data={"username": "nobody", "password": "password123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Invalid" in resp.data

    def test_blank_username_shows_error(self, client):
        resp = client.post(
            "/login",
            data={"username": "", "password": "password123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"required" in resp.data.lower() or b"Invalid" in resp.data


class TestLogoutRoute:

    def test_logout_clears_session_and_redirects(self, client):
        _login(client)
        resp = client.post("/logout", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Customer Login" in resp.data


# ---------------------------------------------------------------------------
# Dashboard route tests
# ---------------------------------------------------------------------------

class TestDashboardRoute:

    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/dashboard", follow_redirects=True)
        assert b"Customer Login" in resp.data

    def test_authenticated_shows_balance(self, client):
        _login(client)
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert b"1,000.00" in resp.data


# ---------------------------------------------------------------------------
# Deposit route tests
# ---------------------------------------------------------------------------

class TestDepositRoute:

    def test_unauthenticated_get_redirects(self, client):
        resp = client.get("/deposit", follow_redirects=True)
        assert b"Customer Login" in resp.data

    def test_valid_deposit_updates_balance(self, client):
        _login(client)
        resp = client.post(
            "/deposit",
            data={"amount": "250"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"1,250.00" in resp.data

    def test_zero_deposit_shows_error(self, client):
        _login(client)
        resp = client.post(
            "/deposit",
            data={"amount": "0"},
            follow_redirects=True,
        )
        assert b"greater than zero" in resp.data.lower()

    def test_negative_deposit_shows_error(self, client):
        _login(client)
        resp = client.post(
            "/deposit",
            data={"amount": "-100"},
            follow_redirects=True,
        )
        assert b"greater than zero" in resp.data.lower()

    def test_non_numeric_deposit_shows_error(self, client):
        _login(client)
        resp = client.post(
            "/deposit",
            data={"amount": "abc"},
            follow_redirects=True,
        )
        assert b"valid number" in resp.data.lower()


# ---------------------------------------------------------------------------
# Withdrawal route tests
# ---------------------------------------------------------------------------

class TestWithdrawRoute:

    def test_unauthenticated_get_redirects(self, client):
        resp = client.get("/withdraw", follow_redirects=True)
        assert b"Customer Login" in resp.data

    def test_valid_withdrawal_updates_balance(self, client):
        _login(client)
        resp = client.post(
            "/withdraw",
            data={"amount": "400"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"600.00" in resp.data

    def test_withdrawal_exceeding_balance_shows_error(self, client):
        _login(client)
        resp = client.post(
            "/withdraw",
            data={"amount": "9999"},
            follow_redirects=True,
        )
        assert b"insufficient" in resp.data.lower()

    def test_zero_withdrawal_shows_error(self, client):
        _login(client)
        resp = client.post(
            "/withdraw",
            data={"amount": "0"},
            follow_redirects=True,
        )
        assert b"greater than zero" in resp.data.lower()

    def test_negative_withdrawal_shows_error(self, client):
        _login(client)
        resp = client.post(
            "/withdraw",
            data={"amount": "-50"},
            follow_redirects=True,
        )
        assert b"greater than zero" in resp.data.lower()

    def test_exact_balance_withdrawal_succeeds(self, client):
        _login(client)
        resp = client.post(
            "/withdraw",
            data={"amount": "1000"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"0.00" in resp.data


# ---------------------------------------------------------------------------
# Error handler tests
# ---------------------------------------------------------------------------

class TestErrorHandlers:

    def test_404_returns_custom_page(self, client):
        resp = client.get("/this-page-does-not-exist")
        assert resp.status_code == 404
        assert b"404" in resp.data
