"""
transactions.py — Business logic for deposit and withdrawal operations.

Responsibilities:
  - Validate input (type conversion, positive value, balance sufficiency).
  - Update the account balance atomically.
  - Record every operation in the transactions ledger.
  - Return (True, success_message) or (False, error_message) — never raise.

This module has NO knowledge of HTTP requests or Flask sessions.
It receives plain Python values and returns plain Python results.
"""

from db import get_db, get_account_by_customer_id, update_balance, record_transaction


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_amount(raw):
    """
    Attempt to convert *raw* to a positive float.

    Returns (float, None)         on success.
    Returns (None, error_string)  on failure.
    """
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None, "Please enter a valid number."

    if value <= 0:
        return None, "Amount must be greater than zero."

    return value, None


def _get_account_or_error(db, customer_id):
    """
    Fetch the account row for *customer_id*.

    Returns (account_row, None)   on success.
    Returns (None, error_string)  if the account does not exist.
    """
    account = get_account_by_customer_id(db, customer_id)
    if account is None:
        return None, "Account not found. Please contact support."
    return account, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_deposit(customer_id, raw_amount):
    """
    Deposit *raw_amount* into the account owned by *customer_id*.

    Validation order:
      1. Parse and validate the amount.
      2. Confirm the account exists.
      3. Add the amount and record the ledger entry.

    Returns (True, success_message) or (False, error_message).
    """
    amount, err = _parse_amount(raw_amount)
    if err:
        return False, err

    db = get_db()
    account, err = _get_account_or_error(db, customer_id)
    if err:
        return False, err

    new_balance = round(account["balance"] + amount, 2)
    update_balance(db, account["id"], new_balance)
    record_transaction(db, account["id"], "deposit", amount)

    return True, f"Successfully deposited ${amount:,.2f}. New balance: ${new_balance:,.2f}."


def process_withdrawal(customer_id, raw_amount):
    """
    Withdraw *raw_amount* from the account owned by *customer_id*.

    Validation order:
      1. Parse and validate the amount.
      2. Confirm the account exists.
      3. Check sufficient balance.
      4. Deduct the amount and record the ledger entry.

    Returns (True, success_message) or (False, error_message).
    """
    amount, err = _parse_amount(raw_amount)
    if err:
        return False, err

    db = get_db()
    account, err = _get_account_or_error(db, customer_id)
    if err:
        return False, err

    if account["balance"] < amount:
        return False, (
            f"Insufficient funds. "
            f"Your current balance is ${account['balance']:,.2f}."
        )

    new_balance = round(account["balance"] - amount, 2)
    update_balance(db, account["id"], new_balance)
    record_transaction(db, account["id"], "withdrawal", amount)

    return True, f"Successfully withdrew ${amount:,.2f}. New balance: ${new_balance:,.2f}."
