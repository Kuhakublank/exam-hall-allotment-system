# Automated Examination Hall Allotment and Seating Arrangement System

Web-based academic software prototype for automating examination hall allotment (First-Fit Decreasing) and constraint-based seating arrangement (Backtracking Search with Minimum Remaining Values and Forward Checking, compared against a Greedy First-Fit baseline).

---

## Technology Stack

- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
- **Backend:** Python 3.15, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF
- **Database:** PostgreSQL 17
- **File Processing:** Pandas, OpenPyXL (added in Phase 4)
- **Reporting:** HTML Print View, ReportLab PDF (added in Phase 9)
- **Optional Verification:** Google OR-Tools CP-SAT (added in Phase 8)
- **Testing:** Pytest

---

## Project Folder Structure

```text
Exam-Hall-Allotment-System/
├── app/
│   ├── __init__.py                   # Flask application factory
│   ├── cli.py                        # Secure Flask CLI commands (create-admin)
│   ├── config.py                     # Environment-based configuration
│   ├── extensions.py                 # SQLAlchemy, Migrate, LoginManager, CSRFProtect
│   ├── models/                       # PostgreSQL database models
│   ├── algorithms/                   # Pure Python hall & seating algorithms
│   │   ├── structures.py             # Shared dataclasses (StudentInput, SeatNode, HallGrid)
│   │   ├── hall_allotment_ffd.py     # First-Fit Decreasing hall allocator
│   │   ├── mrv.py                    # Minimum Remaining Values (MRV) heuristic
│   │   ├── forward_checking.py       # Forward Checking & domain restoration
│   │   ├── backtracking.py           # Main Backtracking seating engine
│   │   ├── greedy.py                 # Greedy First-Fit baseline
│   │   ├── validator.py              # Independent seating constraint validator
│   │   └── cpsat_verifier.py         # Optional OR-Tools CP-SAT verifier
│   ├── services/                     # Business, auth, import, validation & reporting services
│   ├── routes/                       # Modular Flask Blueprints per feature
│   ├── templates/                    # Bootstrap 5 Jinja2 HTML templates
│   └── static/                       # Custom CSS and JavaScript assets
├── docs/                             # Technical specification & DB architecture diagram
├── migrations/                       # Alembic / Flask-Migrate database migrations
├── tests/                            # Automated unit, integration & synthetic tests
├── .env.example                      # Safe environment variable template
├── .gitignore                        # Excludes .env, .venv, and caches from Git
├── requirements.txt                  # Python package dependencies
└── run.py                            # Application entry point
```

---

## Project Setup (Windows)

### 1. Prerequisites
- Python 3.11+ (verified with Python 3.15.2 via `py`)
- PostgreSQL 17 running locally with an empty database named `exam_seating_db`

### 2. Create and Activate the Virtual Environment
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure Environment Variables (`.env`)
Copy `.env.example` to `.env` and replace `YOUR_POSTGRES_PASSWORD` with your local `postgres` user password:
```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-random-secret-key
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/exam_seating_db
```
*(Never commit `.env` to GitHub—it is ignored automatically by `.gitignore`.)*

### 4. Apply Database Migrations
```powershell
flask --app run.py db upgrade
```

### 5. Create the Initial Administrator Account
Create your administrator account interactively (password input is hidden and hashed before saving):
```powershell
.\.venv\Scripts\flask.exe --app run.py create-admin
```
You can also pass options or environment variables (`ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`) in automated setups. Duplicate accounts are rejected automatically.

### 6. Run the Application
```powershell
.\.venv\Scripts\flask.exe --app run.py run
```
Then open `http://127.0.0.1:5000` in your browser and sign in with your administrator email and password.

---

## Running Automated Tests

All tests use isolated synthetic data and never modify your development database:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
