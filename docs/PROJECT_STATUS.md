# NCD Platform — Project Status

## 1. Project Overview

The NCD Platform is a digital health platform for non-communicable disease awareness, prevention, monitoring, and continuity of care. It supports two user roles:

- **Patients** — register, log in, book appointments, view health records, receive notifications, manage settings.
- **Service Providers** (doctors/health workers) — register, log in, manage appointments, view patient lists/details, add consultation notes and follow-ups, manage availability and settings.

The frontend consists of HTML templates served by a Flask application (`app.py`). Data is currently stored in memory (Python lists/dictionaries) inside `app.py`, not in a database.

## 2. Development Environment

- **Location:** `E:\Desktop\ncd-frontend\ncd`
- **Backend:** Flask (`app.py`, 3,132 lines), Python
- **Frontend:** Plain HTML, CSS, JavaScript — no frameworks (no Bootstrap, React, Vue, Angular)
- **Templates:** 23 HTML files in `templates/`
- **Static assets:** `static/css/style.css` (1,539 lines), `static/js/script.js` (153 lines)
- **Entry point:** `index.html` via Flask route `@app.route("/")`
- **Data storage:** In-memory only (no database; data resets on server restart)
- **Authentication:** Flask session-based (cookies), separate patient and provider sessions
- **Python version:** 3.13.5 (system Python, no virtual environment detected)
- **Dependency files:** None — no `requirements.txt`, `pyproject.toml`, `setup.cfg`, or `Pipfile`
- **Installed packages relevant to Flask stack:** None — Flask, SQLAlchemy, Werkzeug, psycopg2/psycopg, and Flask-Migrate are NOT installed
- **PostgreSQL 18:** Installed at `C:\Program Files\PostgreSQL\18\bin\`; service `postgresql-x64-18` is **Running**
- **Existing database configuration:** None in `app.py` (no SQLALCHEMY, database URI, or ORM configuration)

## 3. Completed Work

- Frontend structure and functionality investigation completed. Findings saved in `docs/FRONTEND_AUDIT.md` (502 lines).
- Backend requirements defined and saved in `docs/REQUIREMENTS.md`.

## 4. Important Findings

- **33 Flask routes** across patient and provider features.
- **Missing templates:** `profile.html`, `records.html`, `change-password.html` do not exist (routes `/profile`, `/records`, `/change-password` will fail).
- **Route name mismatches:** 5 `url_for()` calls in templates reference Flask function names that do not exist (e.g., `add_patient_note` vs `add_consultation_note`).
- **Appointment booking is JavaScript-only:** hardcoded demo data, never calls the Flask `/appointments` POST route.
- **Health monitoring, health records, and availability are client-side only** — no backend endpoints receive this data.
- **Settings password change uses `fetch("/settings/change-password")`** but Flask route is `/change-password` — endpoint mismatch.
- **Passwords stored in plain text** in `app.py`.
- No external JS frameworks; Google Fonts used in `availability.html` only.

## 5. Architecture Decision

**Retain Flask as the backend framework.** Do not switch to Django REST Framework.

Planned stack:
- **Framework:** Flask
- **Database:** PostgreSQL (persistent storage)
- **ORM:** SQLAlchemy
- **Password hashing:** Werkzeug (`generate_password_hash`, `check_password_hash`)
- **Frontend:** Retain existing Flask-based HTML/CSS/JavaScript templates
- **Integration:** Backend endpoints must integrate with existing frontend forms and routes

This replaces the previous in-memory `app.config` storage with a PostgreSQL database accessed via SQLAlchemy.

## 6. Current Development Stage

Requirements drafting complete (`docs/REQUIREMENTS.md`). Architecture: Flask + PostgreSQL + SQLAlchemy + Werkzeug. Ready to install dependencies and begin backend implementation.

## 7. Immediate Next Task

Requirements drafted. Environment inspection complete. Missing dependencies: Flask, SQLAlchemy, Werkzeug (standalone), psycopg2/psycopg, Flask-Migrate are not installed. PostgreSQL 18 is installed and running. No virtual environment or dependency files exist.

Smallest next implementation step: Install the required Python packages (Flask, SQLAlchemy, Werkzeug, psycopg2-binary, Flask-Migrate) and verify they import correctly. Do not modify application source code yet.

## 8. Development Rules

- Work in small steps.
- Explain changes before implementation.
- Never modify unrelated files.
- Verify every change.
- Do not repeat completed investigations unnecessarily.
- Do not assume previous chat history is available.
- Keep this status document updated after important milestones.

## 9. AI Session Handoff Instructions

When a new AI chat starts:

1. Read this `PROJECT_STATUS.md` first.
2. Understand the current stage and next task.
3. Do not automatically read the entire `FRONTEND_AUDIT.md`.
4. Consult `FRONTEND_AUDIT.md` only when a specific frontend detail needs verification.
5. Do not repeat completed work unless necessary.
6. Ask for clarification if the actual source code contradicts the documented findings.

---

**File location:** `E:\Desktop\ncd-frontend\ncd\docs\PROJECT_STATUS.md`  
**Related file:** `docs/FRONTEND_AUDIT.md` (full frontend investigation report)