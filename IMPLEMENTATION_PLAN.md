# Banking Web Application — Implementation Plan

> **Document Type:** High-Level Planning Only
> **Status:** Draft
> **Scope:** Frontend (HTML + Bootstrap) · Backend (Python Flask) · Database (SQLite)

---

## 1. Solution Overview

### Objective
Design and deliver a lightweight, browser-based banking web application that allows customers to securely log in, view their account balance, deposit funds, withdraw funds, and log out — all through a clean, responsive interface.

### Scope

| In Scope | Out of Scope |
|---|---|
| Customer login / logout | Admin portal |
| View account balance | Multi-currency support |
| Deposit funds | Third-party payment integrations |
| Withdraw funds | Notifications / email alerts |
| Session-based authentication | Mobile native app |
| Single SQLite database | Role-based access (e.g. teller vs. manager) |

### Users
- **Retail Bank Customer** — the sole user persona; accesses the app via a desktop or mobile browser to manage their own account.

### Functional Requirements

| # | Requirement |
|---|---|
| FR-01 | A registered customer can log in using a username and password. |
| FR-02 | An authenticated customer is redirected to a personal dashboard. |
| FR-03 | The dashboard displays the customer's current account balance. |
| FR-04 | The customer can deposit a positive monetary amount into their account. |
| FR-05 | The customer can withdraw a positive monetary amount, subject to sufficient balance. |
| FR-06 | The customer can log out, ending their session. |
| FR-07 | Unauthenticated requests to protected pages redirect to the login page. |

### Non-Functional Requirements

| # | Requirement |
|---|---|
| NFR-01 | Passwords must be stored hashed — never in plain text. |
| NFR-02 | All protected routes must verify an active session before serving content. |
| NFR-03 | The UI must be responsive and usable on both desktop and mobile viewports. |
| NFR-04 | Deposit and withdrawal operations must validate input (positive numbers, sufficient balance). |
| NFR-05 | The application must run in a local development environment without external services. |

### Assumptions
- A customer account is pre-seeded in the database (self-registration is out of scope).
- A single account per customer is assumed for this version.
- SQLite is sufficient for the expected single-user / low-concurrency usage.
- The Flask development server is acceptable for local deployment.
- Bootstrap 5 CDN is used — no custom build pipeline is required.

---

## 2. High-Level Architecture

### Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                        BROWSER                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │           FRONTEND  (FRONTEND/)                  │     │
│   │  HTML templates rendered by Flask (Jinja2)       │     │
│   │  Bootstrap 5 for layout and responsive styling   │     │
│   └─────────────────────┬────────────────────────────┘     │
└─────────────────────────┼──────────────────────────────────┘
                          │  HTTP Requests (form POST / GET)
                          ▼
┌────────────────────────────────────────────────────────────┐
│                    BACKEND  (BACKEND/)                      │
│   ┌──────────────────────────────────────────────────┐     │
│   │           Python Flask Application               │     │
│   │  Route handlers · Session management             │     │
│   │  Business logic · Input validation               │     │
│   └─────────────────────┬────────────────────────────┘     │
└─────────────────────────┼──────────────────────────────────┘
                          │  SQL queries via SQLite driver
                          ▼
┌────────────────────────────────────────────────────────────┐
│                   DATABASE  (BACKEND/)                      │
│   ┌──────────────────────────────────────────────────┐     │
│   │           SQLite  (bank.db)                      │     │
│   │  Customers · Accounts · Transactions             │     │
│   └──────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────┘
```

### Frontend → Backend → Database Interaction

1. **Browser** sends an HTTP request (GET for page load, POST for form submission) to Flask.
2. **Flask route handler** validates the session cookie; unauthenticated requests are redirected to `/login`.
3. **Business logic layer** (within Flask) validates input, applies rules (e.g. insufficient-balance check).
4. **Data access layer** (within Flask) executes parameterised SQL against `bank.db` and returns results.
5. Flask renders the appropriate **Jinja2 HTML template** and returns it to the browser.

### Request Lifecycle (Authenticated Transaction)

```
Browser                Flask Route          Business Logic        SQLite
   │                       │                      │                  │
   │── POST /deposit ──────►│                      │                  │
   │                       │── validate session ──►│                  │
   │                       │◄─ session OK ─────────│                  │
   │                       │── validate amount ───►│                  │
   │                       │◄─ amount valid ───────│                  │
   │                       │── UPDATE balance ─────┼─────────────────►│
   │                       │◄─ rowcount = 1 ───────┼──────────────────│
   │◄── redirect /dashboard│                       │                  │
```

---

## 3. Component Design

### Frontend Responsibilities (`FRONTEND/`)
- Provide all HTML page templates (login, dashboard, deposit, withdraw) using **Jinja2** syntax so Flask can render them server-side.
- Apply **Bootstrap 5** grid, utility classes, and form components for a responsive, styled UI.
- Display server-side flash messages (success / error feedback) returned by Flask.
- Submit user data via HTML `<form>` elements using standard `POST` requests — no JavaScript fetch/AJAX required.
- Enforce basic client-side input constraints (e.g. `required`, `min`, `type="number"`) as a UX convenience only; server-side validation is authoritative.

### Backend Responsibilities (`BACKEND/`)
- Serve and render all frontend templates via Flask's `render_template`.
- Manage **session state** using Flask's signed cookie session.
- Implement route handlers for: login, logout, dashboard, deposit, withdraw.
- Enforce **authentication guards** on every protected route.
- Execute all **business rules**: password verification, balance sufficiency check, input sanitisation.
- Interact with SQLite through Python's built-in `sqlite3` module using parameterised queries.
- Return appropriate HTTP redirects and flash messages.

### Database Responsibilities (`BACKEND/bank.db`)
- Persist customer credentials (username + hashed password).
- Persist account state (current balance tied to a customer).
- Persist a transaction ledger (amount, type, timestamp) for auditability.
- Enforce referential integrity between customers, accounts, and transactions.

---

## 4. Folder Structure

```
banking-app/
│
├── FRONTEND/                      # All UI assets and templates
│   ├── templates/                 # Jinja2 HTML templates (rendered by Flask)
│   │   ├── base.html              # Shared layout: navbar, flash messages, Bootstrap CDN
│   │   ├── login.html             # Login form page
│   │   ├── dashboard.html         # Customer dashboard — balance + action buttons
│   │   ├── deposit.html           # Deposit form page
│   │   └── withdraw.html          # Withdraw form page
│   └── static/                    # Static files served directly
│       ├── css/
│       │   └── custom.css         # Minor style overrides on top of Bootstrap
│       └── images/                # Logo or any UI imagery
│
├── BACKEND/                       # Python Flask application
│   ├── app.py                     # Flask app factory, route definitions, app entry point
│   ├── auth.py                    # Authentication helpers (login check, session guard)
│   ├── db.py                      # Database connection helper and query functions
│   ├── transactions.py            # Deposit and withdrawal business logic
│   ├── bank.db                    # SQLite database file (auto-created on first run)
│   └── requirements.txt           # Python dependencies (flask, werkzeug, etc.)
│
└── IMPLEMENTATION_PLAN.md         # This document
```

### Responsibility of Each Folder / File

| Path | Responsibility |
|---|---|
| `FRONTEND/templates/` | Server-rendered HTML pages; contain Jinja2 template tags |
| `FRONTEND/templates/base.html` | Master layout inherited by all pages; loads Bootstrap 5 via CDN |
| `FRONTEND/static/css/` | Optional custom CSS overrides |
| `BACKEND/app.py` | Flask app init; all route definitions; `if __name__ == "__main__"` entry point |
| `BACKEND/auth.py` | Password hashing, hash verification, session login/logout helpers, auth decorator |
| `BACKEND/db.py` | Opens SQLite connection, provides helper functions for common queries |
| `BACKEND/transactions.py` | Pure business logic for deposit and withdrawal (balance checks, ledger writes) |
| `BACKEND/bank.db` | SQLite database — created at runtime; not committed to source control |
| `BACKEND/requirements.txt` | Pinned Python package list for reproducible installs |

---

## 5. Module Breakdown

### 5.1 Authentication Module

**Goal:** Verify customer identity and manage session state throughout the session lifecycle.

| Concern | Approach |
|---|---|
| Password storage | Hashed with `werkzeug.security` (`generate_password_hash`) |
| Login verification | Compare submitted password against stored hash (`check_password_hash`) |
| Session creation | Write `user_id` into Flask's signed cookie session on successful login |
| Session termination | Clear session on logout |
| Route protection | A decorator or helper that checks `session["user_id"]` before allowing access to protected routes; redirects to `/login` on failure |

**Pages involved:** `login.html`
**Routes involved:** `GET /login`, `POST /login`, `POST /logout`

---

### 5.2 Dashboard Module

**Goal:** Provide the customer's home screen after login — a summary view with navigation to all actions.

| Concern | Approach |
|---|---|
| Balance display | Query current balance for `session["user_id"]` and pass to template |
| Navigation | Buttons / links to Deposit, Withdraw, Logout |
| Access control | Protected by authentication guard |

**Pages involved:** `dashboard.html`
**Routes involved:** `GET /dashboard`

---

### 5.3 Account Management Module

**Goal:** Allow the application to look up and update customer account data.

| Concern | Approach |
|---|---|
| Account lookup | Fetch account row by customer ID from `db.py` helper |
| Balance read | Return current balance for display on dashboard |
| Balance update | Atomic UPDATE of balance field as part of a deposit or withdrawal |

This module has no standalone page — it is consumed by the Dashboard and Transaction modules.

---

### 5.4 Transactions Module

**Goal:** Process deposit and withdrawal operations safely and record them in the ledger.

| Concern | Approach |
|---|---|
| Deposit | Accept amount → validate positive number → add to balance → record ledger entry |
| Withdrawal | Accept amount → validate positive number → check balance sufficiency → deduct from balance → record ledger entry |
| Insufficient funds | Return error flash message; do not modify balance |
| Invalid input | Server-side check for non-numeric or zero/negative values; return error flash |
| Feedback | Flash success or error message; redirect to dashboard |

**Pages involved:** `deposit.html`, `withdraw.html`
**Routes involved:** `GET /deposit`, `POST /deposit`, `GET /withdraw`, `POST /withdraw`

---

## 6. Implementation Roadmap

### Phase Overview

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
Setup       Auth        Dashboard   Transactions  Polish
```

---

### Phase 1 — Project Setup & Scaffold

**Goal:** Establish the project structure, install dependencies, and wire together a "hello world" Flask app that can serve a template.

| Item | Detail |
|---|---|
| Tasks | Create folder structure; install Flask + Werkzeug; configure `app.py`; verify template rendering |
| Deliverable | Flask dev server starts; visiting `http://localhost:5000` returns a rendered HTML page |
| Effort | Low |
| Dependencies | None |

---

### Phase 2 — Database Initialisation & Authentication

**Goal:** Set up the SQLite database with seed data and implement the full login/logout flow.

| Item | Detail |
|---|---|
| Tasks | Create `db.py`; define and initialise tables; seed one customer account; implement `auth.py`; build login route and template |
| Deliverable | A customer can log in with correct credentials and be redirected to a placeholder dashboard; incorrect credentials show an error; logout clears the session |
| Effort | Medium |
| Dependencies | Phase 1 complete |

---

### Phase 3 — Dashboard & Balance View

**Goal:** Build the authenticated dashboard that displays the customer's current balance.

| Item | Detail |
|---|---|
| Tasks | Implement `GET /dashboard` route; query and display balance in `dashboard.html`; apply authentication guard |
| Deliverable | Logged-in customer sees their balance on the dashboard; unauthenticated access redirects to login |
| Effort | Low |
| Dependencies | Phase 2 complete |

---

### Phase 4 — Deposit & Withdrawal Transactions

**Goal:** Implement the deposit and withdrawal features with full server-side validation.

| Item | Detail |
|---|---|
| Tasks | Implement `transactions.py`; build deposit and withdraw routes and templates; handle error flash messages for invalid input and insufficient funds |
| Deliverable | Customer can deposit and withdraw funds; balance updates correctly; edge cases (negative amount, zero, insufficient balance) show appropriate errors |
| Effort | Medium |
| Dependencies | Phase 3 complete |

---

### Phase 5 — UI Polish & End-to-End Review

**Goal:** Ensure the UI is consistent, accessible, and the full user journey is tested manually.

| Item | Detail |
|---|---|
| Tasks | Apply Bootstrap 5 styling consistently across all pages; validate responsive layout on mobile viewport; review all flash message feedback; verify all redirect paths |
| Deliverable | Fully styled, responsive application with a consistent look and feel across all pages |
| Effort | Low |
| Dependencies | Phase 4 complete |

---

### Phase Dependency Summary

| Phase | Depends On |
|---|---|
| Phase 1 — Setup | — |
| Phase 2 — Auth | Phase 1 |
| Phase 3 — Dashboard | Phase 2 |
| Phase 4 — Transactions | Phase 3 |
| Phase 5 — Polish | Phase 4 |

---

*End of Implementation Plan*
