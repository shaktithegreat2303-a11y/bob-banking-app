# SecureBank — Banking Web Application

A lightweight, full-stack banking application built with **HTML + Bootstrap 5**
(frontend) and **Python Flask + SQLite** (backend).

---

## Features

| Feature | Route |
|---|---|
| Customer login | `GET/POST /login` |
| Dashboard with balance | `GET /dashboard` |
| Deposit funds | `GET/POST /deposit` |
| Withdraw funds | `GET/POST /withdraw` |
| Logout | `POST /logout` |

---

## Project Structure

```
banking-app/
├── FRONTEND/
│   ├── templates/          # Jinja2 HTML templates
│   │   ├── base.html       # Shared layout + Bootstrap 5 CDN
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── deposit.html
│   │   ├── withdraw.html
│   │   └── errors/
│   │       ├── 404.html
│   │       └── 500.html
│   └── static/
│       └── css/
│           └── custom.css
│
└── BACKEND/
    ├── app.py              # Flask app, all routes
    ├── auth.py             # Login verification, session helpers, route guard
    ├── db.py               # SQLite connection, schema, seed data, query helpers
    ├── transactions.py     # Deposit & withdrawal business logic
    ├── requirements.txt    # Python dependencies
    ├── .env                # Environment variables (not committed to git)
    └── tests/
        ├── conftest.py
        ├── test_unit.py        # 20 unit tests (auth + transactions)
        └── test_integration.py # 20 integration tests (all routes)
```

---

## Quick Start

### 1. Clone / open the project

```
cd banking-app/BACKEND
```

### 2. Create and activate the virtual environment

```bash
# Windows
py -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables (optional)

Copy `.env` and set your own `SECRET_KEY`:

```
SECRET_KEY=your-random-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=1
```

### 5. Run the application

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Demo Credentials

| Username | Password |
|---|---|
| `demo_user` | `password123` |

The demo account is seeded automatically on first run with a **$1,000.00**
starting balance.

---

## Running Tests

With the virtual environment active:

```bash
# From the workspace root
pytest banking-app/BACKEND/tests/ -v
```

Expected: **40 passed**.

---

## Security Notes

- Passwords are stored as **bcrypt-style hashes** via `werkzeug.security`.
- Sessions use Flask's **signed cookie** — the server never stores session data.
- All SQL uses **parameterised queries** — no string concatenation.
- The `.env` file and `bank.db` are excluded from git via `.gitignore`.
- For production: use Gunicorn/Waitress, HTTPS, and a strong random `SECRET_KEY`.
