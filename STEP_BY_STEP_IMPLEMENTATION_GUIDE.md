# Banking Web Application — Step-by-Step Implementation Guide

> **Reference:** [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
> **Document Type:** Implementation Instructions (plain English logic — no full code)
> **Stack:** HTML · Bootstrap 5 · Python Flask · SQLite

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Backend Implementation](#2-backend-implementation)
3. [Frontend Implementation](#3-frontend-implementation)
4. [Integration Steps](#4-integration-steps)
5. [Validation Rules](#5-validation-rules)
6. [Testing](#6-testing)
7. [Deployment](#7-deployment)

---

## 1. Environment Setup

### Step 1.1 — Create the Project Directory Structure

Start by creating the root project folder, then create the two top-level sub-folders exactly as planned:

```
banking-app/
├── FRONTEND/
│   ├── templates/
│   └── static/
│       └── css/
└── BACKEND/
```

Create these folders manually or via your terminal. The `FRONTEND/templates/` folder is where Flask will look for HTML pages. The `BACKEND/` folder is where all Python files and the database will live.

---

### Step 1.2 — Install Python

Confirm Python 3.9 or higher is installed on your machine. Open a terminal and check the version. If it is not installed, download it from the official Python website. Python 3 includes `pip` (the package installer) and `sqlite3` (the database driver) out of the box — no extra installation needed for those.

---

### Step 1.3 — Create a Virtual Environment

Navigate your terminal into the `BACKEND/` folder. Create a virtual environment there. A virtual environment is an isolated Python installation that keeps your project's dependencies separate from other Python projects on your system.

**How it works conceptually:**
- Python copies a lightweight interpreter and a `site-packages` folder into a new local directory (commonly named `venv`).
- When you activate it, your terminal's `python` and `pip` commands point to that local copy instead of the global one.
- All packages you install go into `venv/site-packages` and do not affect anything outside the project.

Activate the virtual environment after creating it. On Windows the activation command is different from macOS/Linux — use the appropriate one for your operating system. You will know it is active because your terminal prompt will be prefixed with the environment name.

> **Rule:** Always activate the virtual environment before running any `pip install` or `python` command for this project.

---

### Step 1.4 — Install Dependencies

With the virtual environment active, install the two required packages:

| Package | Purpose |
|---|---|
| `flask` | The web framework — handles routing, templating, and sessions |
| `werkzeug` | Comes bundled with Flask; provides the password hashing utilities |

Install both in a single `pip install` command. After installation, create a `requirements.txt` file in `BACKEND/` by running `pip freeze > requirements.txt`. This file records the exact versions installed so anyone else can reproduce the environment later.

---

### Step 1.5 — Verify Flask Is Working

Create a minimal `app.py` in `BACKEND/` that:
1. Imports Flask.
2. Creates a Flask application instance.
3. Defines a single route at the root URL (`/`) that returns a plain text response like "Banking App is running".
4. Starts the development server when the file is run directly.

Run `app.py` from your terminal and open `http://localhost:5000` in a browser. If you see the text response, Flask is set up correctly and you can proceed.

---

## 2. Backend Implementation

### Step 2.1 — Create the Database Helper (`db.py`)

`db.py` is responsible for all communication with the SQLite database. It should do three things:

**Connection management:**
Write a function that opens a connection to `bank.db` (located in the `BACKEND/` folder). SQLite will create the file automatically if it does not yet exist. Configure the connection to return rows as dictionary-like objects so you can access columns by name rather than by index.

**Table initialisation:**
Write a function that creates all three tables if they do not already exist:
- A `customers` table to store the customer's username and hashed password.
- An `accounts` table to store the current balance, linked to the customer by a foreign key.
- A `transactions` table to store every deposit and withdrawal as a log entry, linked to the account.

Use `CREATE TABLE IF NOT EXISTS` so that calling this function multiple times is safe.

**Seed data:**
Write a function that inserts a test customer if no customers exist yet. Generate a hashed password using `werkzeug`'s `generate_password_hash` and store the hash — never the plain text password. Create a matching account row with an initial starting balance. This gives you a working login credential for development without needing a registration screen.

Call the initialisation and seeding functions once when the Flask app starts up.

---

### Step 2.2 — Create the Authentication Helper (`auth.py`)

`auth.py` handles everything related to proving who the user is and protecting routes.

**Login verification logic:**
Write a function that accepts a username and a plain text password. It should query the `customers` table for a row matching the username. If no row is found, return a failure result. If a row is found, use `werkzeug`'s `check_password_hash` to compare the submitted password against the stored hash. Return success only if the hash comparison passes.

**Session creation:**
After a successful login verification, store the customer's unique ID in Flask's `session` object (e.g. `session["user_id"] = customer_id`). Flask signs this value and sends it to the browser as a secure cookie. On all subsequent requests, Flask reads the cookie and makes `session["user_id"]` available again.

**Authentication decorator (route guard):**
Write a function decorator that wraps any route you want to protect. The decorator checks whether `session["user_id"]` is present and valid. If it is not, the decorator redirects the visitor to the login page before the route handler runs. Apply this decorator to every route except login.

**Logout logic:**
Write a function that calls `session.clear()` to remove all session data, then redirects to the login page.

---

### Step 2.3 — Define Flask Routes in `app.py`

Routes are the URLs the browser visits and the Python functions that respond to them. Organise them in `app.py` in this logical order:

**`GET /` → Redirect**
The root URL should simply redirect to `/login`. This way there is no blank page when a user first opens the app.

**`GET /login` → Show login form**
Render the `login.html` template. If the user is already logged in (session exists), redirect them to `/dashboard` immediately — no need to log in again.

**`POST /login` → Process login**
Read the `username` and `password` fields from the submitted form. Call the authentication verification function from `auth.py`. On success, create the session and redirect to `/dashboard`. On failure, flash an error message ("Invalid username or password") and re-render the login page.

**`GET /dashboard` → Show dashboard**
Protected by the auth decorator. Query the account balance for the logged-in user (using `session["user_id"]`). Pass the balance and the customer's name to `dashboard.html` for rendering.

**`GET /deposit` → Show deposit form**
Protected by the auth decorator. Render the `deposit.html` template.

**`POST /deposit` → Process deposit**
Protected by the auth decorator. Read the `amount` field from the form. Call the deposit logic from `transactions.py`. On success, flash a success message and redirect to `/dashboard`. On failure, flash the error and re-render the deposit page.

**`GET /withdraw` → Show withdraw form**
Protected by the auth decorator. Render the `withdraw.html` template, passing the current balance so the form can hint the maximum amount.

**`POST /withdraw` → Process withdrawal**
Protected by the auth decorator. Read the `amount` field from the form. Call the withdrawal logic from `transactions.py`. On success, flash a success message and redirect to `/dashboard`. On failure (insufficient funds or invalid input), flash the error and re-render the withdraw page.

**`POST /logout` → Log out**
Call the logout helper from `auth.py`. Clear the session and redirect to `/login`.

---

### Step 2.4 — Create the Transaction Service (`transactions.py`)

`transactions.py` contains pure business logic — it does not deal with HTTP requests or templates. It only takes inputs, applies rules, talks to the database, and returns a result.

**Deposit function:**
- Accept the `customer_id` and the raw `amount` value.
- Validate that the amount is a valid number (convert it safely; catch any conversion error).
- Validate that the amount is greater than zero.
- If validation passes, fetch the current balance from `db.py`, add the deposit amount, and update the balance in the `accounts` table using a parameterised query.
- Insert a row into the `transactions` table recording the type as "deposit", the amount, and the current timestamp.
- Return a success result.
- If any validation fails, return a failure result with a descriptive error message.

**Withdrawal function:**
- Accept the `customer_id` and the raw `amount` value.
- Validate the amount is a valid, positive number (same as deposit).
- Fetch the current balance from the database.
- Check that the balance is greater than or equal to the withdrawal amount. If not, return a failure result with "Insufficient funds".
- If sufficient, subtract the amount from the balance and update the `accounts` table.
- Insert a row into the `transactions` table recording the type as "withdrawal", the amount, and the timestamp.
- Return a success result.

> **Key design principle:** Neither function should ever modify the balance unless all validations have already passed. Treat validation and data modification as two separate, sequential stages.

---

### Step 2.5 — Session Management

Flask sessions work via a signed browser cookie. Here is the complete mental model:

1. When the user logs in, you write `session["user_id"] = <id>`. Flask serialises this dictionary, signs it with your app's `SECRET_KEY`, and sends it to the browser as a cookie.
2. On every subsequent request the browser automatically sends the cookie back. Flask reads, verifies the signature, and reconstructs the session dictionary so your route handlers can access `session["user_id"]`.
3. Because the cookie is cryptographically signed, the user cannot modify it without invalidating the signature. This is what makes it safe to trust `session["user_id"]` as proof of identity.
4. When the user logs out, `session.clear()` removes all data from the dictionary. Flask sends an updated (now empty) cookie to the browser.

**Important configuration:** Set `app.secret_key` to a long, random string before running the app. Without a secret key, Flask cannot sign cookies and sessions will not work. Store this value as an environment variable in production — never hard-code it in source code.

---

### Step 2.6 — Error Handling

**Flash messages:** Use Flask's `flash()` function to pass one-time messages from a route handler to the next rendered page. Flash messages are stored in the session for exactly one request and then discarded. Categories like `"success"` and `"error"` allow the template to display them with appropriate styling.

**HTTP error pages:** Register custom handlers for 404 (page not found) and 500 (server error) in `app.py`. Each handler should render a simple template with a friendly message rather than showing Flask's default technical error page to the user.

**Database errors:** Wrap database write operations (INSERT, UPDATE) in try/except blocks. If the database raises an exception, roll back the transaction, log the error for the developer, and return a user-friendly error message rather than crashing.

---

## 3. Frontend Implementation

### Step 3.1 — Create the Base Layout (`base.html`)

Before building individual pages, create a shared base template that all pages will inherit from. This avoids repeating the same HTML boilerplate on every page.

The base template should include:
- The full HTML5 document structure (`<!DOCTYPE html>`, `<head>`, `<body>`).
- A `<link>` tag in the `<head>` loading Bootstrap 5 from its CDN URL.
- A Bootstrap navbar at the top showing the app name ("SecureBank" or similar). When a user is logged in, the navbar should show a "Logout" button on the right. When logged out, show nothing or just the brand name.
- A container `<div>` in the `<body>` where flash messages will be displayed. Loop through all flash messages from Flask and render each one as a Bootstrap alert — green for success, red for error.
- A Jinja2 `block content` tag. This is a named placeholder that child templates will fill in with their own page-specific HTML.
- A `<script>` tag at the bottom loading Bootstrap's JavaScript bundle from the CDN.

Every other template will start with `{% extends "base.html" %}` and place its content inside `{% block content %}`.

---

### Step 3.2 — Build the Login Page (`login.html`)

The login page should be centred on the screen. Use Bootstrap's grid to create a narrow, centred card.

Inside the card:
- A heading like "Customer Login".
- A form with `method="POST"` and `action="/login"`.
- A text input for "Username" with Bootstrap's `form-control` class and the `required` attribute.
- A password input for "Password" with the same styling and the `required` attribute.
- A submit button labelled "Login" styled with Bootstrap's `btn btn-primary`.

The form should not do any client-side login logic. It simply packages the inputs and submits them to the server. Flask handles everything else.

---

### Step 3.3 — Build the Dashboard (`dashboard.html`)

The dashboard is the customer's home screen. It should feel welcoming and clear.

Layout approach:
- A large welcome heading: "Welcome, [customer name]" — inject the name via a Jinja2 template variable.
- A prominent balance card in the centre. Display "Current Balance" as a label and the formatted balance as the value (e.g. `$1,250.00`). Use a Bootstrap card with a clear visual hierarchy.
- Three action buttons below the balance card: "Deposit", "Withdraw", and "Logout". Each should be a distinct Bootstrap button colour (e.g. green for deposit, yellow for withdraw, red for logout).
- "Deposit" and "Withdraw" are standard `<a>` link buttons pointing to `/deposit` and `/withdraw`. "Logout" should be inside a small `<form>` that POSTs to `/logout` — do not use a plain link for logout, as logout must be a POST action to prevent accidental logouts via prefetching.

---

### Step 3.4 — Build the Deposit Form (`deposit.html`)

The deposit page should be simple and focused.

Layout approach:
- A heading: "Deposit Funds".
- A short descriptive line explaining what the form does.
- A form with `method="POST"` and `action="/deposit"`.
- A single numeric input labelled "Amount" with `type="number"`, a `min` attribute of `0.01`, a `step` attribute of `0.01` (to allow cents), and the `required` attribute.
- A submit button labelled "Deposit".
- A "Back to Dashboard" link below the form for easy navigation.

---

### Step 3.5 — Build the Withdraw Form (`withdraw.html`)

The withdraw page mirrors the deposit page but adds balance context so the customer knows what is available.

Layout approach:
- A heading: "Withdraw Funds".
- A small informational line showing the customer's current balance — e.g. "Available balance: $1,250.00". Inject this from the Flask route as a template variable.
- A form with `method="POST"` and `action="/withdraw"`.
- A numeric input for "Amount" with the same `type`, `min`, `step`, and `required` attributes as the deposit form.
- A submit button labelled "Withdraw".
- A "Back to Dashboard" link.

---

### Step 3.6 — Apply Bootstrap Layout Principles

Across all pages, follow these Bootstrap conventions for a consistent, responsive result:

| Principle | How to apply it |
|---|---|
| **Responsive container** | Wrap all page content in `<div class="container">` or `<div class="container-fluid">` |
| **Centred cards** | Use `<div class="row justify-content-center">` with a column like `col-md-6` to centre narrow forms |
| **Form controls** | Apply `form-control` to all inputs, `form-label` to all labels, and `mb-3` to each field group for spacing |
| **Button styles** | Use `btn btn-primary` for primary actions, `btn btn-outline-secondary` for navigation links |
| **Alert messages** | Render flash messages as `<div class="alert alert-success">` or `<div class="alert alert-danger">` depending on the category |
| **Spacing** | Use Bootstrap margin/padding utilities (`mt-4`, `py-3`, etc.) rather than custom CSS wherever possible |

---

## 4. Integration Steps

### Step 4.1 — Connect Flask to the Frontend Templates

Flask needs to know where to find your HTML templates and static files. By default Flask looks for templates in a folder named `templates/` and static files in `static/` relative to the application file. Since your templates live in `FRONTEND/templates/` (not inside `BACKEND/`), you must explicitly tell Flask where to find them.

When creating the Flask application instance, pass two keyword arguments:
- `template_folder` — the relative or absolute path pointing to `FRONTEND/templates/`.
- `static_folder` — the relative or absolute path pointing to `FRONTEND/static/`.

Once this is configured, all `render_template("login.html")` calls will resolve to `FRONTEND/templates/login.html`, and Bootstrap's CDN link tag will still load from the internet, so no further setup is needed for styles.

---

### Step 4.2 — Connect Flask Routes to Templates

Each route handler and its template must agree on the variable names passed between them:

| Route | Template | Variables passed from Flask |
|---|---|---|
| `GET /login` | `login.html` | None |
| `GET /dashboard` | `dashboard.html` | `customer_name`, `balance` |
| `GET /deposit` | `deposit.html` | None |
| `GET /withdraw` | `withdraw.html` | `balance` |

Pass these as keyword arguments to `render_template`. In the template, reference them using Jinja2 double-brace syntax: `{{ balance }}`.

---

### Step 4.3 — Connect Flask to SQLite

Flask itself has no built-in database layer — you use Python's standard `sqlite3` module directly.

**Connection strategy:**
Open a new database connection at the start of each request and close it at the end. Flask provides two special hooks for this:
- `@app.before_request` — runs before every route handler; open the connection and attach it to Flask's `g` object (a per-request global store).
- `@app.teardown_appcontext` — runs after every request completes; close the connection stored in `g`.

This pattern ensures no connections are leaked and each request works with a fresh, clean connection.

**Query pattern:**
When you need to read or write data, call the connection stored on `g` and use parameterised queries — always pass user-supplied values as parameters (using `?` placeholders), never by string concatenation. This prevents SQL injection.

---

### Step 4.4 — Wire Form Submissions to Backend Logic

The flow for every form submission is:

1. Browser fills in the form and clicks submit.
2. Browser sends a POST request with form data encoded in the request body.
3. Flask route handler reads the form values using `request.form["field_name"]`.
4. The handler calls the appropriate function in `transactions.py` or `auth.py`.
5. The service function does its work and returns either a success or a failure result.
6. The route handler reads the result: on success, flash a success message and `redirect()`; on failure, flash the error message and `render_template()` the form again.

The redirect-after-POST pattern (also called PRG — Post/Redirect/Get) is important. Redirecting after a successful POST means that if the user hits browser refresh, they will not accidentally re-submit the form.

---

## 5. Validation Rules

### Step 5.1 — Login Validation

Apply these checks in the `POST /login` route handler before calling any database query:

| Check | Rule | Error message |
|---|---|---|
| Username not empty | The submitted username field must not be blank | "Username is required" |
| Password not empty | The submitted password field must not be blank | "Password is required" |
| Credentials match | The username must exist in the database AND the password must match the stored hash | "Invalid username or password" |

> **Security note:** Always use the same generic error message ("Invalid username or password") whether the username does not exist or the password is wrong. Different messages for each case would let an attacker figure out which usernames are valid.

---

### Step 5.2 — Balance Validation

Apply these checks in `db.py` before any account balance read or write:

| Check | Rule |
|---|---|
| Account exists | The account row for the given `customer_id` must exist before any read or write |
| Balance is a number | The stored balance value must be a valid decimal — this should always be true if writes go through the service layer |

These checks are defensive guards to catch unexpected data states.

---

### Step 5.3 — Deposit Validation

Apply these checks in `transactions.py` inside the deposit function, in this exact order:

| Step | Check | Rule | Error message |
|---|---|---|---|
| 1 | Type conversion | Attempt to convert the submitted value to a float. If conversion fails, stop immediately | "Please enter a valid number" |
| 2 | Positive value | The converted amount must be strictly greater than zero | "Deposit amount must be greater than zero" |
| 3 | Reasonable upper bound (optional) | Optionally enforce a maximum single deposit limit | "Amount exceeds the maximum allowed deposit" |

Only if all checks pass should you proceed to update the database.

---

### Step 5.4 — Withdrawal Validation

Apply these checks in `transactions.py` inside the withdrawal function, in this exact order:

| Step | Check | Rule | Error message |
|---|---|---|---|
| 1 | Type conversion | Attempt to convert the submitted value to a float. Stop if it fails | "Please enter a valid number" |
| 2 | Positive value | The converted amount must be strictly greater than zero | "Withdrawal amount must be greater than zero" |
| 3 | Sufficient balance | Fetch the current balance. The balance must be greater than or equal to the withdrawal amount | "Insufficient funds. Your current balance is $X" |

Only if all three checks pass should you proceed to deduct the amount and record the transaction.

---

## 6. Testing

### Step 6.1 — Unit Tests

Unit tests verify individual functions in isolation, without a running server or real database.

**What to unit test:**

| Function | Test cases |
|---|---|
| Deposit logic in `transactions.py` | Valid amount succeeds · Zero amount fails · Negative amount fails · Non-numeric string fails |
| Withdrawal logic in `transactions.py` | Valid amount with sufficient balance succeeds · Amount exceeding balance fails · Zero amount fails · Negative amount fails |
| Password hash check in `auth.py` | Correct password returns True · Wrong password returns False · Empty password returns False |

**How to write unit tests:**
Use Python's built-in `unittest` module or the `pytest` library (install via pip). For database-dependent functions, create a temporary in-memory SQLite database (`":memory:"` as the database path) before each test and dispose of it after. This means your tests never touch the real `bank.db` file and always start from a clean state.

---

### Step 6.2 — Integration Tests

Integration tests verify that the HTTP layer (routes) and the data layer (SQLite) work together correctly.

**What to integration test:**

| Scenario | Expected behaviour |
|---|---|
| POST `/login` with valid credentials | Redirects to `/dashboard`, session contains `user_id` |
| POST `/login` with wrong password | Returns 200, login page is re-rendered, error flash message present |
| GET `/dashboard` without a session | Redirects to `/login` |
| POST `/deposit` with valid amount | Redirects to `/dashboard`, balance increases by the deposited amount |
| POST `/deposit` with negative amount | Returns 200, deposit page re-rendered, error flash present |
| POST `/withdraw` exceeding balance | Returns 200, withdraw page re-rendered, "Insufficient funds" flash present |
| POST `/logout` | Session is cleared, redirects to `/login` |

**How to write integration tests:**
Use Flask's built-in test client (`app.test_client()`). The test client lets you send simulated HTTP requests and inspect responses without starting a real server. Use a separate test database (a temporary in-memory SQLite database) so tests do not corrupt development data. Set `app.config["TESTING"] = True` to disable error catching so exceptions surface properly during tests.

---

### Step 6.3 — Manual Testing Checklist

After all automated tests pass, walk through this checklist manually in the browser to verify the end-to-end user experience:

**Authentication flow:**
- [ ] Opening `http://localhost:5000` redirects to the login page.
- [ ] Submitting the login form with blank fields shows the required field error.
- [ ] Submitting with a wrong password shows "Invalid username or password".
- [ ] Submitting with correct credentials redirects to the dashboard.
- [ ] Typing `/dashboard` directly in the address bar while logged out redirects to login.

**Dashboard:**
- [ ] Dashboard shows the correct customer name.
- [ ] Dashboard shows the correct account balance.
- [ ] Deposit, Withdraw, and Logout buttons are visible and clickable.

**Deposit:**
- [ ] Submitting a valid amount shows a success flash and updated balance on the dashboard.
- [ ] Submitting zero shows an error message.
- [ ] Submitting a negative number shows an error message.
- [ ] Submitting text (non-numeric) shows an error message.

**Withdrawal:**
- [ ] Submitting an amount less than the balance shows success and the balance is reduced.
- [ ] Submitting an amount greater than the balance shows "Insufficient funds".
- [ ] Submitting zero or negative shows appropriate errors.

**Logout:**
- [ ] Clicking Logout clears the session and redirects to login.
- [ ] After logout, pressing the browser back button and trying to access `/dashboard` redirects to login.

**Responsive layout:**
- [ ] Open browser developer tools, switch to a mobile viewport (e.g. iPhone SE).
- [ ] Verify all pages are readable and usable at small screen widths without horizontal scrolling.

---

## 7. Deployment

### Step 7.1 — Run Locally

To start the application on your development machine:

1. Open a terminal and navigate to the `BACKEND/` folder.
2. Activate the virtual environment.
3. Run `python app.py`. Flask will start the development server and print the URL (default: `http://127.0.0.1:5000`).
4. Open that URL in your browser. The database file (`bank.db`) will be created automatically on first run and the seed customer will be inserted.
5. To stop the server, press `Ctrl + C` in the terminal.

> The Flask development server is single-threaded and restarts automatically when you save changes to Python files (debug mode). This is ideal for local development but is not suitable for real users.

---

### Step 7.2 — Environment Variables

Before moving beyond local development, move sensitive configuration out of `app.py` and into environment variables:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask's signing key for session cookies — must be a long, random string |
| `DATABASE_PATH` | The file path to `bank.db`, so it can be changed per environment |
| `FLASK_ENV` | Set to `development` locally and `production` on a server |

On your local machine, set these in a `.env` file and use the `python-dotenv` library to load them automatically when the app starts. On a production server, set them as system-level environment variables or through the hosting platform's secrets management.

> **Never commit the `.env` file or `SECRET_KEY` values to source control.** Add `.env` and `bank.db` to your `.gitignore` file.

---

### Step 7.3 — Production Considerations

The following changes are required before the application is suitable for real users:

| Concern | What to do |
|---|---|
| **WSGI server** | Replace the Flask development server with a production-grade WSGI server such as **Gunicorn** (Linux/macOS) or **Waitress** (Windows). These servers handle multiple concurrent requests safely. |
| **HTTPS** | Serve the application over HTTPS only. Use a reverse proxy like **Nginx** in front of the WSGI server and configure an SSL certificate (e.g. via Let's Encrypt). Session cookies must use `Secure` and `HttpOnly` flags. |
| **Database** | SQLite is suitable for single-user or very low traffic. For any real usage, consider migrating to PostgreSQL or MySQL with a proper connection pool. |
| **Secret key** | Set `SECRET_KEY` to a cryptographically random value of at least 32 bytes. Rotate it if compromised — this will invalidate all active sessions. |
| **Debug mode** | Ensure `debug=False` in production. Debug mode exposes an interactive debugger in the browser that gives arbitrary code execution access to anyone who can reach an error page. |
| **Logging** | Configure Python's `logging` module to write errors to a persistent log file so you can diagnose issues after deployment. |
| **Static files** | Serve `FRONTEND/static/` files directly through Nginx rather than through Flask for better performance. |

---

*End of Step-by-Step Implementation Guide*
