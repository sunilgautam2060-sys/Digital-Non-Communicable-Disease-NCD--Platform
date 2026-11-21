# NCD Platform — Project Status

## 1. Project Overview

The NCD Platform is a digital health platform for non-communicable disease awareness, prevention, monitoring, and continuity of care. It supports two user roles:

- **Patients** — register, log in, book appointments, view health records, receive notifications, manage settings.
- **Service Providers** (doctors/health workers) — register, log in, manage appointments, view patient lists/details, add consultation notes and follow-ups, manage availability and settings.

The frontend consists of HTML templates served by a Flask application (`app.py`). Patient and provider accounts and the appointment workflow use PostgreSQL through SQLAlchemy. Several other features still use in-memory or client-side storage.

## 2. Development Environment

- **Location:** `E:\Desktop\ncd-frontend\ncd`
- **Backend:** Flask (`app.py`, 3,132 lines), Python
- **Frontend:** Plain HTML, CSS, JavaScript — no frameworks (no Bootstrap, React, Vue, Angular)
- **Templates:** 23 HTML files in `templates/`
- **Static assets:** `static/css/style.css` (1,539 lines), `static/js/script.js` (153 lines)
- **Entry point:** `index.html` via Flask route `@app.route("/")`
- **Data storage:** Accounts, appointments, health records, medication logs, provider availability, notes/follow-ups, and patient notification preferences persist in PostgreSQL; some display preferences and informational pages remain client-side or static
- **Authentication:** Flask session-based (cookies), separate patient and provider sessions
- **Python version:** 3.13.5 (system Python)
- **Virtual environment:** `.venv` at `E:\Desktop\ncd-frontend\ncd\.venv` (Python 3.13.5)
- **Dependency files:** `requirements.txt` created with 15 packages
- **Installed packages:**
  - Flask==3.1.3
  - Flask-SQLAlchemy==3.1.1
  - Flask-Migrate==4.1.0
  - psycopg2-binary==2.9.13
  - SQLAlchemy==2.1.9
  - Werkzeug==3.1.9
  - python-dotenv==1.2.4
  - (plus transitive dependencies: alembic, blinker, click, itsdangerous, Jinja2, Mako, MarkupSafe, typing_extensions)
- **PostgreSQL 18:** Installed at `C:\Program Files\PostgreSQL\18\bin\`; service `postgresql-x64-18` is **Running**
- **Database configuration:** ✅ Added to `app.py` — SQLAlchemy URI from `DATABASE_URL`, `SQLALCHEMY_TRACK_MODIFICATIONS=False`, `db` and `migrate` initialized
- **Database connection:** ✅ Verified successful (PostgreSQL 18, database `ncd_platform`)
- **Configuration files:**
  - `.gitignore` ✅ Created (excludes .venv, __pycache__, .env, instance/, etc.)
  - `.env.example` ✅ Created (placeholders for SECRET_KEY, DATABASE_URL)
  - `.env` ✅ Created (real credentials — ignored by Git, not committed)

## 3. Completed Work

- Frontend structure and functionality investigation completed. Findings saved in `docs/FRONTEND_AUDIT.md` (502 lines).
- Backend requirements defined and saved in `docs/REQUIREMENTS.md`.
- **Python virtual environment created** at `.venv` with Python 3.13.5.
- **Dependencies installed:** Flask, Flask-SQLAlchemy, Flask-Migrate, psycopg2-binary, Werkzeug (via Flask), python-dotenv.
- **requirements.txt created** with 15 packages (direct + transitive).
- **Import verification passed:** flask, flask_sqlalchemy, flask_migrate, psycopg2, werkzeug, dotenv all import successfully.
- **Application visually inspected** running at `http://127.0.0.1:5000` via `.venv` Flask development server.
- **Provider registration/login issues investigated** (see Section 10).
- **Project configuration prepared for database integration:**
  - `.gitignore` created (excludes .venv, __pycache__, .env, instance/, etc.)
  - `.env.example` created with SECRET_KEY and DATABASE_URL placeholders
  - python-dotenv installed and added to requirements.txt
  - Verified `.env` is correctly ignored by Git
- **SQLAlchemy models created and migration applied:**
  - `models.py` created with Patient, Provider, Appointment, HealthRecord, ConsultationNote, FollowUp, ProviderSettings
  - `flask db init` → `flask db migrate` → `flask db upgrade` executed successfully
  - **7 new tables created**: `patient`, `provider`, `appointment`, `health_record`, `consultation_note`, `follow_up`, `provider_settings`
  - Migration version `80e02a7b45bd` recorded in `alembic_version`
  - Existing Django tables preserved (no drops, no cascade)
  - App imports verified; database connection verified
- **Patient/provider authentication connected to SQLAlchemy:**
  - Registration and login use the Patient and Provider models
  - Passwords are stored as Werkzeug hashes and checked with `check_password_hash`
  - Duplicate registration and invalid-login messages are displayed in the existing templates
  - Provider form first/last name fields are combined for the model's `fullname`
  - Provider identity helper reads the provider associated with the current session
  - Verification passed with Flask's test client and a temporary in-memory SQLite database; PostgreSQL was not used for test accounts
- **Appointment workflow connected to SQLAlchemy:**
  - Patient booking, listing, rescheduling, and cancellation use the `appointment` table
  - Providers can view assigned appointments and confirm, reject, cancel, or complete permitted statuses
  - Patient/provider ownership is checked on the server
  - Provider choices are loaded from registered provider accounts; demo appointment rows were removed
  - Patient and provider notifications, provider appointment counts, and provider patient lists use database appointments
  - Migration `b7c4d2e91a63` added nullable `service` and `location` columns and was applied to PostgreSQL without dropping existing tables
  - Full route flow and access checks passed on isolated in-memory SQLite; PostgreSQL was used only to apply and inspect the schema migration
- **Direct app launch fixed:** moved the shared SQLAlchemy object to `extensions.py`, so `app.py` and `models.py` no longer import each other. `python app.py` was verified to start the Flask server using an isolated SQLite URL; no PostgreSQL data was changed during this launch check.
- **Provider patient pages unblocked:** added the missing `/patients` route, corrected the patient details template path, and aligned template endpoint names with Flask routes
- **Patient profile and health records pages unblocked:** added `profile.html` and `records.html`; records are scoped to the logged-in patient and loaded from `health_record`
- **Patient weight now persists:** monitoring reads the latest weight entries from `health_record`; the authenticated `/monitoring/weight` endpoint validates and saves new values
- **Provider dashboard demo content removed:** summary counts and recent appointment/patient/activity panels now use the logged-in provider's database appointments and show empty states when none exist
- **Provider appointment action fixed:** `last_action_by` now stores the role value `provider`, which fits its `String(20)` column instead of storing a potentially longer email address
- **Shared appearance applied across templates:** added shared theme CSS/JavaScript and fixed broken dashboard/monitoring `script.js` paths; both patient and provider saved theme settings are read
- **Password change flow repaired:** added the missing page, aligned the settings URL with Flask, and made the endpoint return JSON for the settings modal while retaining form support
- **Provider patient detail not-found path repaired:** inaccessible or missing patient IDs redirect to the provider patient list instead of rendering with a null patient
- **Verification passed on isolated in-memory SQLite:** current app/model import; patient profile, records, monitoring, provider dashboard; weight save; provider appointment confirmation using a long email; password update; and all 27 GET routes without server errors. No PostgreSQL test data was created.
- **Local browser smoke check:** home, patient login, and provider login pages load from Flask; the saved dark appearance carries from home to patient login. The original light appearance was restored after the check. A read-only PostgreSQL `SELECT 1` succeeded. Authenticated PostgreSQL pages still need a manual check while signed into existing accounts.
- **Authenticated patient browser check:** dashboard, profile, records, monitoring, and appointments loaded using the user's signed-in session. Existing record and weight displays were present; no health data was submitted or modified. Fixed the dashboard header to use the signed-in name from the Flask session instead of browser-only storage.
- **Authenticated provider browser check:** dashboard, appointment list, patient list, patient detail modal, consultation workspace, and follow-up page loaded. Dashboard rows match provider-owned database records; demo names are absent. Fixed provider name/type to come from the Flask session. No appointment status or patient data was changed.
- **Consultation notes and follow-ups now persist:** note create/edit/delete and follow-up create/list/complete routes use SQLAlchemy models with provider/patient ownership checks. Follow-ups accept the date-only form, and optional appointment links are stored.
- **Migration `c39a70f2d841` applied and verified on PostgreSQL:** added nullable appointment links to consultation notes and follow-ups, and made follow-up time nullable to match the date-only form. Read-only schema inspection confirmed the revision and columns. Route flows passed with isolated SQLite; no test notes or follow-ups were written to PostgreSQL.
- **Provider availability and booking checks now use PostgreSQL:** added nullable JSON `availability_config` to `provider_settings` in migration `1d6e8c3f4a20`. Availability loads/saves per provider; booking and rescheduling validate weekly hours, breaks, date exceptions, and conflicts with pending/confirmed appointments. The availability page loaded in the provider browser without JavaScript errors; no live schedule was submitted. Isolated SQLite checks passed for save/load, invalid schedules, off days, breaks, and appointment conflicts.
- **Patient measurements now persist:** blood pressure, blood glucose, thyroid TSH, and weight are saved to `health_record` by the authenticated patient. Monitoring summaries and history read from PostgreSQL and show empty states instead of example values or uncalculated “Normal” labels. Isolated SQLite checks passed for saves, display, input validation, and patient ownership.
- **Patient medication tracking now persists:** added patient-owned medication entries and one intake log per medication per day. The monitoring page now shows an empty state instead of fictional medication examples, and supports adding a medication and marking today's dose as taken. The authenticated routes validate inputs and enforce patient ownership. Isolated SQLite checks passed for saving, display, idempotent daily logging, invalid input, and cross-patient access; no medication data was written to PostgreSQL.
- **Migration `2f8c1a6d4e90` applied and verified on PostgreSQL:** created `medication` and `medication_log`, with patient/medication foreign keys and a unique medication/date constraint. The Alembic revision and columns were inspected after upgrade.
- **Patient notification preferences now persist automatically:** each change to the three notification switches on `/settings` is posted to an authenticated endpoint and the page shows Saving/Saved/error status; language, appearance, and timezone remain browser preferences handled by Save Settings. Appointment alerts control whether updates appear on `/notifications`; health-reminder and health-information choices are stored but those notification types are not generated yet, as the UI explains. Isolated SQLite checks verified save/reload and patient isolation; the browser toggle itself still needs a manual retest.
- **Migration `7a4c9e2d6b31` applied and verified on PostgreSQL:** added nullable `patient.notification_preferences`; existing accounts retain defaults until a patient saves preferences.
- **Inactive patient settings clarified:** removed the browser-only profile-visibility, health-data-sharing, and remember-login toggles because they did not change server behavior. The page now explains current role/assignment-based access and session behavior, marks these options unavailable in English and Nepali, and removes their stale localStorage values. Isolated settings-page rendering checks passed; no access policy or session behavior was changed.
- **Integrated role smoke check passed on isolated SQLite:** patient and provider login both succeeded, followed by 10 authenticated GET pages for each role. The fixtures included an appointment, health record, medication, and follow-up so the data-backed pages rendered with representative rows. No PostgreSQL patient data was read or changed during this check.
- **Source review of informational/data templates:** `/prevention` and `/community` intentionally serve static MVP education pages. The active `/appointments` template receives registered providers and appointments from database-backed Flask routes; corrected an old comment that called these demo providers. The separate `templates/health records.html` file is a legacy, unreferenced prototype and is not served; the active `/records` route uses `records.html` with patient-owned database records.

## 4. Important Findings

- **36 Flask route rules** across patient and provider features.
- **Patient template errors fixed:** patient `profile.html`, `records.html`, and `change-password.html` now exist and their routes were exercised on isolated SQLite.
- **Appointment fees are still display estimates** from the frontend’s existing service pricing; no payment or fee records are stored.
- Medication tracking, health measurements, provider availability, consultation notes, follow-ups, patient notification preferences, provider notification/privacy/account preferences, and patient-owned health record deletion are database-backed. Language/appearance and some display preferences remain browser-side.
- Authentication, appointment, and health-record delete workflows were exercised in a manually used isolated SQLite browser session; no real patient/provider data was used.
- Requirements review found the essential MVP and important follow-up items implemented. Password reset, CSRF protection, dynamic prevention/community pages, patient-list search, and exports are listed as optional future improvements.
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

Patient/provider accounts, appointments, measurement records, medications and daily intake logs, consultation notes, follow-ups, provider availability, patient notification preferences, and provider notification/privacy/account preferences are stored in PostgreSQL via SQLAlchemy. Language/appearance, some other display preferences, and informational features remain client-side or static.

## 6. Current Development Stage

Requirements review: all essential MVP items and the listed important follow-up features are implemented. Manual acceptance passed against isolated SQLite: the patient submitted a synthetic appointment and saw it after refresh, then deleted the synthetic health record. A direct database check confirmed one test booking remained and the synthetic record was gone. No real patient/provider data was used. Additive migrations are applied to PostgreSQL. Prevention/community pages remain intentionally static, and one legacy health-record template is unreferenced.

## 7. Immediate Next Task

**Database setup, models, authentication, and the core appointment workflow are implemented.** Appointment migration `b7c4d2e91a63` is applied to PostgreSQL. End-to-end route checks used temporary in-memory SQLite to avoid inserting test accounts into PostgreSQL.

The patient confirmed that an appointment form refreshed before submission loses its unsaved draft by design. Manual acceptance against isolated SQLite passed: a submitted appointment remained visible after refresh, and the synthetic health record disappeared after deletion. A direct database check confirmed both outcomes. The local test server was stopped and `instance/manual_qa.sqlite` was removed. **MVP status: complete. Next task: choose an optional future improvement if development is continuing.**

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

## 11. Database Integration Readiness Inspection (Pending Approval)

### 11.1 Current app.py Structure
| Aspect | Status | Detail |
|--------|--------|--------|
| **Flask app creation** | Direct | `app = Flask(__name__)` at module level (line 6) — **not an application factory** |
| **Route organization** | Monolithic | All 33 routes in single `app.py` file (lines 850–3132) |
| **In-memory storage** | `app.config` | 11 keys: `registered_user`, `registered_provider`, `appointments`, `patients`, `consultation_notes`, `followups`, counters, `provider_settings` |
| **Authentication** | Session-based | `patient_required` / `provider_required` decorators check `session["logged_in"]` / `session["provider_logged_in"]` |
| **Secret key** | Hardcoded | `app.secret_key = "ncd-nepal-secret-key"` (line 7) — must move to env var |

**Assessment:** Current structure works for demo but needs small adjustments before database integration:
- Move secret key to environment variable
- Add SQLAlchemy config (`SQLALCHEMY_DATABASE_URI`, `SQLALCHEMY_TRACK_MODIFICATIONS`)
- Initialize `db = SQLAlchemy(app)` and `migrate = Migrate(app, db)`
- Can remain monolithic for MVP; factory pattern optional but not required

### 11.2 PostgreSQL Readiness
| Check | Result |
|-------|--------|
| **Service running** | ✅ `postgresql-x64-18` service is **Running** |
| **Version** | ✅ PostgreSQL 18.6 (`psql` available) |
| **Connection test** | ✅ Verified via SQLAlchemy engine — connects to `ncd_platform` database |
| **Existing databases** | `ncd_platform` accessible with provided credentials |
| **Project database** | ✅ Exists and accessible |

### 11.3 Existing Configuration
| File | Exists | Notes |
|------|--------|-------|
| `.gitignore` | ✅ Yes | Created — excludes .venv, __pycache__, .env, instance/, etc. |
| `.env.example` | ✅ Yes | Created — placeholders for SECRET_KEY, DATABASE_URL |
| `.env` | ✅ Yes | Real credentials — ignored by Git, not committed |
| `requirements.txt` | ✅ Yes | 15 packages pinned |

### 11.4 Installed Package Versions (in `.venv`)
- Flask-SQLAlchemy: **3.1.1**
- Flask-Migrate: **4.1.0**
- SQLAlchemy: **2.1.9**
- psycopg2-binary: **2.9.13**
- Werkzeug: **3.1.9**

### 11.5 Proposed Minimum Models for MVP

#### Patient
```python
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    address = db.Column(db.Text)
    account_type = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)  # Werkzeug hash
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationships
    appointments = db.relationship("Appointment", back_populates="patient")
    health_records = db.relationship("HealthRecord", back_populates="patient")
```

#### Provider
```python
class Provider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    provider_type = db.Column(db.String(30), nullable=False)  # doctor, nurse, etc.
    specialization = db.Column(db.String(60))
    organization = db.Column(db.String(120))
    location = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationships
    appointments = db.relationship("Appointment", back_populates="provider")
    consultation_notes = db.relationship("ConsultationNote", back_populates="provider")
    followups = db.relationship("FollowUp", back_populates="provider")
    settings = db.relationship("ProviderSettings", back_populates="provider", uselist=False)
```

#### Appointment
```python
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("provider.id"), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    consultation_type = db.Column(db.String(50))
    condition_reason = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending", nullable=False)  # Pending, Confirmed, Rejected, Cancelled, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notification_message = db.Column(db.Text)
    last_action_by = db.Column(db.String(20))  # "patient" or "provider"
    last_action_at = db.Column(db.DateTime)
    # Relationships
    patient = db.relationship("Patient", back_populates="appointments")
    provider = db.relationship("Provider", back_populates="appointments")
```

**Relationships Summary:**
- **Patient ↔ Appointment**: One-to-Many (Patient has many Appointments)
- **Provider ↔ Appointment**: One-to-Many (Provider has many Appointments)
- **Appointment** is the join table linking Patient and Provider
- Future models (HealthRecord, ConsultationNote, FollowUp, ProviderSettings) extend from these

### 11.6 Next Implementation Step (Exact)
1. ✅ Create `.gitignore` (exclude `.venv`, `__pycache__`, `.env`, `*.pyc`, instance folder)
2. ✅ Create `.env.example` with `SECRET_KEY` and `DATABASE_URL` placeholders
3. ✅ Install `python-dotenv` and add to `requirements.txt`
4. ✅ **Create `.env`** with real `SECRET_KEY` and `DATABASE_URL=postgresql+psycopg2://postgres:***@localhost:5432/ncd_platform`
5. ✅ **Update `app.py`:**
   - Load config from environment using `load_dotenv()`
   - Add `SQLALCHEMY_DATABASE_URI`, `SQLALCHEMY_TRACK_MODIFICATIONS=False`
   - Initialize `db = SQLAlchemy(app)`, `migrate = Migrate(app, db)`
   - **Require `SECRET_KEY` and `DATABASE_URL`** (no silent defaults)
6. ✅ **Create `models.py`** with Patient, Provider, Appointment, HealthRecord, ConsultationNote, FollowUp, ProviderSettings
7. ✅ Run `flask db init` → `flask db migrate -m "Initial migration"` → `flask db upgrade`
8. ✅ **Verify tables created** — 7 new tables confirmed in PostgreSQL

**Status: Essential MVP and important follow-up features in `docs/REQUIREMENTS.md` are implemented. Patient/provider authentication, appointments, health monitoring and records, medication tracking, notifications, provider availability and settings, consultation notes, and follow-ups use the database. Migrations `b7c4d2e91a63`, `c39a70f2d841`, `1d6e8c3f4a20`, `2f8c1a6d4e90`, and `7a4c9e2d6b31` are applied and verified in PostgreSQL. Manual acceptance in isolated SQLite confirmed appointment reload after submit and deletion of a synthetic health record; no real records were used. The unsubmitted form draft clears on refresh by design. The manual QA server and database have been cleaned up. MVP complete; optional improvements remain outside the MVP.**

**File location:** `E:\Desktop\ncd-frontend\ncd\docs\PROJECT_STATUS.md`  
**Related file:** `docs/FRONTEND_AUDIT.md` (full frontend investigation report)
