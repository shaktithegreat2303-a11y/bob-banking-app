"""
app.py — Flask application factory, route definitions, and entry point.

Route map:
  GET  /              → redirect to /login
  GET  /login         → render login form
  POST /login         → validate credentials, create session, redirect to /dashboard
  GET  /dashboard     → show balance & action buttons  [protected]
  GET  /deposit       → render deposit form            [protected]
  POST /deposit       → process deposit                [protected]
  GET  /withdraw      → render withdraw form           [protected]
  POST /withdraw      → process withdrawal             [protected]
  POST /logout        → clear session, redirect to /login

Error handlers:
  404 → custom not-found page
  500 → custom server-error page
"""

import os
import sys

# ---------------------------------------------------------------------------
# Make sure BACKEND/ is on sys.path so sibling modules are importable
# whether we run via 'python app.py' or via pytest from the project root.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from flask import Flask, render_template, request, redirect, url_for, flash, session
from dotenv import load_dotenv

load_dotenv()  # load .env file if present

from db import init_db, close_db, get_db, get_customer_by_username, get_account_by_customer_id
from auth import verify_login, login_user, logout_user, login_required
from transactions import process_deposit, process_withdrawal

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

# Resolve paths to the FRONTEND folder which lives one level above BACKEND/
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)
_TEMPLATE_DIR = os.path.join(_ROOT_DIR, "FRONTEND", "templates")
_STATIC_DIR = os.path.join(_ROOT_DIR, "FRONTEND", "static")

app = Flask(
    __name__,
    template_folder=_TEMPLATE_DIR,
    static_folder=_STATIC_DIR,
)

# Secret key: read from environment variable; fall back to dev default only.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Register the close_db teardown so every request releases its connection.
app.teardown_appcontext(close_db)

# Create tables and seed data once at startup.
init_db(app)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Root URL: redirect authenticated users to dashboard, others to login."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ── Authentication ──────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form (GET) or validate credentials and start a session (POST)."""
    # Already logged in → skip the form
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        ok, result = verify_login(username, password)
        if ok:
            login_user(result["id"])
            flash(f"Welcome back, {result['username']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash(result, "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    """Destroy the session and redirect to the login page."""
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))


# ── Dashboard ───────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    """Show the customer's current balance and navigation actions."""
    db = get_db()
    customer_id = session["user_id"]

    customer = db.execute(
        "SELECT username FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()

    account = get_account_by_customer_id(db, customer_id)

    return render_template(
        "dashboard.html",
        customer_name=customer["username"] if customer else "Customer",
        balance=account["balance"] if account else 0.0,
    )


# ── Deposit ─────────────────────────────────────────────────────────────────

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Show the deposit form (GET) or process a deposit (POST)."""
    if request.method == "POST":
        raw_amount = request.form.get("amount", "")
        ok, message = process_deposit(session["user_id"], raw_amount)
        flash(message, "success" if ok else "error")
        if ok:
            return redirect(url_for("dashboard"))
        # On failure, fall through and re-render the form with the flash message.

    return render_template("deposit.html")


# ── Withdrawal ──────────────────────────────────────────────────────────────

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    """Show the withdrawal form (GET) or process a withdrawal (POST)."""
    db = get_db()
    account = get_account_by_customer_id(db, session["user_id"])
    current_balance = account["balance"] if account else 0.0

    if request.method == "POST":
        raw_amount = request.form.get("amount", "")
        ok, message = process_withdrawal(session["user_id"], raw_amount)
        flash(message, "success" if ok else "error")
        if ok:
            return redirect(url_for("dashboard"))
        # On failure, re-render the form so the user sees the current balance.

    return render_template("withdraw.html", balance=current_balance)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
