"""
tests/conftest.py — Shared pytest configuration.

Adds the BACKEND directory to sys.path so all test files can import
app, db, auth, and transactions without installing the package.
"""
import sys
import os

_BACKEND = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
