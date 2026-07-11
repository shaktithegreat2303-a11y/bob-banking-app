"""
auth.py — Authentication helpers.

Responsibilities:
  - Verify a plain-text password against the stored hash.
  - Create and destroy Flask sessions.
  - Provide a login_required decorator that guards protected routes.
"""

from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import check_password_hash

from db import get_db, get_customer_by_username


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def login_user(customer_id):
    """Write the customer's ID into the signed session cookie."""
    session.clear()
    session["user_id"] = customer_id


def logout_user():
    """Remove all session data, effectively logging the user out."""
    session.clear()


# ---------------------------------------------------------------------------
# Login verification
# ---------------------------------------------------------------------------

def verify_login(username, password):
    """
    Check the submitted credentials against the database.

    Returns (True, customer_row)  on success.
    Returns (False, error_string) on failure.

    Always returns the same generic error message for wrong username or
    wrong password to prevent user-enumeration attacks.
    """
    if not username or not username.strip():
        return False, "Username is required."
    if not password:
        return False, "Password is required."

    db = get_db()
    customer = get_customer_by_username(db, username.strip())

    if customer is None or not check_password_hash(customer["password"], password):
        return False, "Invalid username or password."

    return True, customer


# ---------------------------------------------------------------------------
# Route guard decorator
# ---------------------------------------------------------------------------

def login_required(view_func):
    """
    Decorator that redirects to /login when the visitor has no active session.
    Apply to every route that must be accessed only by authenticated customers.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped
