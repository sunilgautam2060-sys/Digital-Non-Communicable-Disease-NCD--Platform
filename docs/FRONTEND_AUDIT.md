# NCD Platform Frontend Audit

**Project:** Digital Non-Communicable Diseases (NCD) Platform  
**Status:** Investigation complete — documentation for future AI sessions  
**Source:** Manual inspection of `app.py`, HTML templates, CSS, and JavaScript  
**Date:** 2026-11-19  
**Verified by:** Kilo Code (investigation agent)  

---

## 1. Project Overview

The NCD Platform is a digital health platform for non-communicable disease awareness, prevention, monitoring, and continuity of care. It supports two user roles:

- **Patients** — register, log in, book appointments, view health records, receive notifications, manage settings.
- **Service Providers** (doctors/health workers) — register, log in, manage appointments, view patient lists/details, add consultation notes and follow-ups, manage availability and settings.

The frontend consists of HTML templates served by a Flask application (`app.py`). Data is currently stored in memory (Python lists/dictionaries) inside `app.py`, not in a database.

**No external JavaScript frameworks** are used (no Bootstrap, jQuery, React, Vue, Angular). Styling is custom CSS. Icons are Unicode/emoji characters. The only external resource is Google Fonts (referenced in `availability.html`).

---

## 2. Existing Project Structure

```
ncd/                              <- project root
├── app.py                        <- Flask application (routes + in-memory data storage)
├── static/
│   ├── css/
│   │   └── style.css             <- Dashboard stylesheet (1,539 lines)
│   └── js/
│       └── script.js             <- Shared JavaScript (153 lines): sidebar toggle,
│                                    theme/appearance (light/dark/system), mark-medication
├── templates/                    <- 23 HTML templates
│   ├── index.html                <- Public home / landing page
│   ├── login.html                <- Patient login
│   ├── register.html             <- Patient registration
│   ├── dashboard.html            <- Patient dashboard
│   ├── monitoring.html           <- Health monitoring
│   ├── prevention.html           <- Prevention / education info
│   ├── community.html            <- Community page
│   ├── appointments.html         <- Book / view patient appointments
│   ├── notifications.html        <- Patient notifications
│   ├── settings.html             <- Patient account settings
│   ├── follow_up.html            <- Follow-up care (provider-only route)
│   ├── consultation.html         <- Consultation page (provider-only route)
│   ├── patients.html             <- Patient list (provider side)
│   ├── patients_details.html     <- Patient detail view (provider side)
│   ├── service_provider.html     <- Provider dashboard
│   ├── provider_login.html       <- Provider login
│   ├── provider_register.html    <- Provider registration
│   ├── provider_profile.html     <- Provider profile
│   ├── provider_settings.html    <- Provider settings
│   ├── provider_notifications.html <- Provider notifications
│   ├── provider_appointments.html <- Provider appointment management
│   ├── availability.html         <- Provider availability
│   └── health records.html       <- Health records (note: space in filename)
```

**Main entry point:** `index.html`, served by Flask route `@app.route("/")`.

**Missing templates referenced by routes (verified):** `profile.html`, `records.html`, `change-password.html` do not exist in `templates/`. Routes `/profile`, `/records`, `/change-password` will fail with `TemplateNotFound` if visited.

**Filename concern:** `health records.html` contains a space. Flask route `/records` references `records.html` (no space), which does not exist.

---

## 3. Complete Flask Route Inventory

All routes defined in `app.py`. Two auth decorators: `patient_required` (checks `session["logged_in"]`) and `provider_required` (checks `session["provider_logged_in"]`).

### Patient-Facing Routes

| # | URL | Template | Methods | Auth | What It Does | Reads/Writes |
|---|-----|----------|---------|------|--------------|--------------|
| 1 | `/` | `index.html` | GET | None | Public home/landing page | None |
| 2 | `/register` | `register.html` | GET, POST | None | Patient registration | Writes `registered_user` |
| 3 | `/login` | `login.html` | GET, POST | None | Patient login | Reads `registered_user`, writes session |
| 4 | `/dashboard` | `dashboard.html` | GET | patient_required | Patient dashboard | Reads session |
| 5 | `/monitoring` | `monitoring.html` | GET | patient_required | Health monitoring page | None |
| 6 | `/prevention` | `prevention.html` | GET | patient_required | Prevention/education info | None |
| 7 | `/community` | `community.html` | GET | patient_required | Community page | None |
| 8 | `/profile` | `profile.html` | GET | patient_required | Patient profile | Reads session |
| 9 | `/records` | `records.html` | GET | patient_required | Patient health records | Reads appointments |
| 10 | `/appointments` | `appointments.html` | GET, POST | patient_required | Book/view appointments | Writes/reads appointments |
| 11 | `/notifications` | `notifications.html` | GET | patient_required | Patient notifications | Builds from appointments |
| 12 | `/settings` | `settings.html` | GET, POST | patient_required | Patient settings | Writes `registered_user`, session |
| 13 | `/change-password` | `change-password.html` | GET, POST | patient_required | Patient password change | Writes `registered_user` |
| 14 | `/logout` | (redirect) | GET | None | Patient logout | Clears session |

### Provider-Facing Routes

| # | URL | Template | Methods | Auth | What It Does | Reads/Writes |
|---|-----|----------|---------|------|--------------|--------------|
| 15 | `/provider-register` | `provider_register.html` | GET, POST | None | Provider registration | Writes `registered_provider` |
| 16 | `/provider-login` | `provider_login.html` | GET, POST | None | Provider login | Reads `registered_provider`, writes session |
| 17 | `/service-provider` | `service_provider.html` | GET | provider_required | Provider dashboard | Reads appointments, patients |
| 18 | `/provider-appointments` | `provider_appointments.html` | GET | provider_required | Provider appointment list | Reads appointments |
| 19 | `/provider-appointments/<int:id>/<action>` | (redirect) | POST | provider_required | Confirm/reject/cancel/complete appointment | Writes appointment status |
| 20 | `/patients` | `patients.html` | GET | provider_required | Provider patient list | Reads patients/appointments |
| 21 | `/patients/<patient_id>` | `patient_details.html` | GET | provider_required | Patient detail view | Reads patient, notes, followups |
| 22 | `/patients/<patient_id>/add-note` | (redirect) | POST | provider_required | Add consultation note | Writes `consultation_notes` |
| 23 | `/patients/<patient_id>/edit-note/<int:note_id>` | (redirect) | POST | provider_required | Edit consultation note | Writes `consultation_notes` |
| 24 | `/patients/<patient_id>/delete-note/<int:note_id>` | (redirect) | POST | provider_required | Delete consultation note | Writes `consultation_notes` |
| 25 | `/patients/<patient_id>/add-followup` | (redirect) | POST | provider_required | Add follow-up | Writes `followups` |
| 26 | `/patients/<patient_id>/followup/<int:followup_id>/complete` | (redirect) | POST | provider_required | Mark follow-up complete | Writes `followups` |
| 27 | `/consultation` | `consultation.html` | GET | provider_required | Provider consultation page | Reads patients |
| 28 | `/follow-up` | `follow_up.html` | GET | provider_required | Provider follow-up list | Reads followups |
| 29 | `/availability` | `availability.html` | GET | provider_required | Provider availability | None |
| 30 | `/provider-notifications` | `provider_notifications.html` | GET | provider_required | Provider notifications | Builds from appointments |
| 31 | `/provider-profile` | `provider_profile.html` | GET | provider_required | Provider profile | Reads session |
| 32 | `/provider-settings` | `provider_settings.html` | GET, POST | provider_required | Provider settings | Writes provider data/settings |
| 33 | `/provider-logout` | (redirect) | GET | None | Provider logout | Clears session |

### Template Files Referenced by Routes That Do Not Exist (verified)

- `profile.html` — referenced by `/profile`
- `records.html` — referenced by `/records` (actual file: `health records.html`)
- `change-password.html` — referenced by `/change-password`

### Route Name Mismatches (verified — will cause `BuildError` on `url_for()`)

The following `url_for()` calls in templates reference Flask endpoint names that do not exist:

| Template | `url_for()` call used | Actual Flask function name | Match? |
|----------|----------------------|---------------------------|--------|
| `patients_details.html` | `add_patient_note` | `add_consultation_note` | ❌ No |
| `patients_details.html` | `delete_patient_note` | `delete_consultation_note` | ❌ No |
| `patients_details.html` | `edit_patient_note` | `edit_consultation_note` | ❌ No |
| `patients_details.html` | `add_patient_followup` | `add_followup` | ❌ No |
| `patients_details.html` + `follow_up.html` | `complete_patient_followup` | `complete_followup` | ❌ No |

---

## 4. Patient Functionality

### 4.1 Registration (`register.html` → `/register`)
- **Verified:** Form `id="registerForm"`, `method="POST"`, `action="{{ url_for('register') }}"`.
- **Fields collected:** fullname, email, phone, date_of_birth, gender, address, account_type, password, confirm_password, terms (checkbox).
- **Connected to backend:** Yes. Flask validates required fields, password match, stores in `app.config["registered_user"]`, redirects to login.

### 4.2 Login (`login.html` → `/login`)
- **Verified:** Form `id="loginForm"`, `method="POST"`, `action="{{ url_for('login') }}"`.
- **Fields collected:** email, password.
- **Connected to backend:** Yes. Flask validates credentials against `registered_user`, sets session variables (`logged_in`, `email`, `fullname`, `phone`, `date_of_birth`, `gender`, `address`, `account_type`), redirects to dashboard.

### 4.3 Dashboard (`dashboard.html` → `/dashboard`)
- **Verified:** GET route, `@patient_required`. Renders template with `fullname` from session.
- **Functionality:** Welcome banner, navigation to monitoring, prevention, community, appointments, records, notifications, settings, profile, logout.
- **Connected to backend:** Yes (renders template with session data). No form submission.

### 4.4 Health Monitoring (`monitoring.html` → `/monitoring`)
- **Verified:** GET route, `@patient_required`.
- **Functionality:** Record/view blood pressure, glucose, weight readings. Mark medications as taken via `markTaken(button)` JavaScript.
- **Connected to backend:** **No.** All data handled client-side only. JavaScript functions: `openReadingModal()`, `saveReading()`, `openWeightModal()`, `saveWeight()`, `markTaken()`. No Flask endpoint receives monitoring data.

### 4.5 Health Records (`health records.html` → `/records`)
- **Verified:** Route `/records` references `records.html` which does not exist. Actual file is `health records.html` (with space).
- **Functionality:** View/delete health records via JavaScript (`viewRecord()`, `deleteRecord()`).
- **Connected to backend:** **No.** Client-side only.

### 4.6 Appointments (`appointments.html` → `/appointments`)
- **Verified:** GET, POST route, `@patient_required`.
- **Form:** `<form id="bookingForm" onsubmit="bookAppointment(event)">` — **no `action` attribute**, handled entirely by JavaScript.
- **Fields collected (via JS):** service, doctor/provider, date, time, type, location, reason.
- **Connected to backend:** **No.** `bookAppointment()` stores data in a local JavaScript array (`appointments.unshift(newAppointment)`) and updates the UI. Hardcoded demo doctors and demo appointments exist in the template's `<script>` block. Flask's `/appointments` POST route exists but is never called by the frontend.

### 4.7 Notifications (`notifications.html` → `/notifications`)
- **Verified:** GET route, `@patient_required`.
- **Connected to backend:** Yes. Flask builds notifications from appointment data via `build_patient_notifications()`. Template has `data-appointments-url="{{ url_for('appointments') }}"` but no fetch call was found using it.

### 4.8 Profile (`profile.html` → `/profile`)
- **Status:** Template `profile.html` does not exist. Route will fail with `TemplateNotFound`.
- **Connected to backend:** Route exists but template missing.

### 4.9 Settings (`settings.html` → `/settings`)
- **Verified:** GET, POST route, `@patient_required`.
- **Functionality:** Update fullname, phone, address (via POST form); change password (via JavaScript `fetch()`).
- **Connected to backend:** Partially. Account settings form POSTs to Flask. Password change uses `fetch("/settings/change-password", ...)` — **endpoint mismatch**: Flask route is `/change-password`, not `/settings/change-password`. Flask returns HTML templates, not JSON, so `await response.json()` will fail.

### 4.10 Follow-up (`follow_up.html` → `/follow-up`)
- **Verified:** Route requires `provider_required` — this is a provider-only page, not patient-facing despite the name.
- **Connected to backend:** Yes (GET only).

### 4.11 Consultation (`consultation.html` → `/consultation`)
- **Verified:** Route requires `provider_required` — provider-only page.
- **Forms:** `consultationForm` (method="POST", no action) and `followupForm` (method="POST", no action). Handled by JavaScript only, not submitted to Flask.

---

## 5. Service Provider Functionality

### 5.1 Provider Registration (`provider_register.html` → `/provider-register`)
- **Fields collected:** fullname, email, phone, provider_type, specialization, organization, location, password, confirm_password.
- **Connected to backend:** Yes (route exists). Form action needs verification.

### 5.2 Provider Login (`provider_login.html` → `/provider-login`)
- **Verified:** Form `action="/provider-login" method="POST"` — hardcoded URL, not `url_for()`.
- **Fields collected:** email, password.
- **Connected to backend:** Yes. Flask validates, sets provider session (`provider_logged_in`, `provider_fullname`, `provider_email`, `provider_phone`, `provider_type`, `provider_specialization`, `provider_organization`, `provider_location`), redirects to `/service-provider`.

### 5.3 Provider Dashboard (`service_provider.html` → `/service-provider`)
- **Verified:** GET route, `@provider_required`.
- **Functionality:** View appointment counts (total, pending, confirmed, completed), patient list.
- **Connected to backend:** Yes. Flask passes stats and patient list to template.

### 5.4 Patient List & Details (`patients.html` → `/patients`, `patients_details.html` → `/patients/<id>`)
- **Verified:** GET routes, `@provider_required`.
- **Functionality:** View patient list with appointment history; view patient details including notes and followups.
- **Connected to backend:** Yes.

### 5.5 Consultation Notes (`patients_details.html`)
- **Forms reference route names that don't match Flask functions (verified mismatches):**
  - `add_patient_note` → Flask has `add_consultation_note`
  - `delete_patient_note` → Flask has `delete_consultation_note`
  - `edit_patient_note` → Flask has `edit_consultation_note`
- These `url_for()` calls will raise `BuildError` when the template is rendered.

### 5.6 Follow-ups (`patients_details.html`, `follow_up.html`)
- **Forms reference route names that don't match Flask functions (verified mismatches):**
  - `add_patient_followup` → Flask has `add_followup`
  - `complete_patient_followup` → Flask has `complete_followup`

### 5.7 Appointment Management (`provider_appointments.html` → `/provider-appointments`)
- **Verified:** GET route, `@provider_required`.
- **Functionality:** View appointments, confirm/reject/cancel/complete via `/provider-appointments/<int:appointment_id>/<action>` POST route.
- **Connected to backend:** Yes.

### 5.8 Availability (`availability.html` → `/availability`)
- **Verified:** GET route, `@provider_required`. Passes `settings` dict (duration, buffer, break_enabled, break_start, break_end).
- **Functionality:** Set weekly schedule, save exceptions via `saveSchedule()`, `copyMondayToWeekdays()`, `resetSchedule()`.
- **Connected to backend:** **No.** Per code comment in `app.py`: "The current availability page stores its schedule in browser localStorage." No data sent to Flask.

### 5.9 Provider Profile (`provider_profile.html` → `/provider-profile`)
- **Verified:** GET route, `@provider_required`. Passes session data (fullname, email, phone, provider_type, specialization, organization, location).
- **Connected to backend:** Yes.

### 5.10 Provider Settings (`provider_settings.html` → `/provider-settings`)
- **Verified:** GET, POST route, `@provider_required`.
- **Functionality:** Save account preferences, notification settings, privacy settings, change password. Three forms POST to `action="{{ url_for('provider_settings') }}"`.
- **Connected to backend:** Yes. Flask handles different actions via `request.form.get("action")`.

### 5.11 Provider Notifications (`provider_notifications.html` → `/provider-notifications`)
- **Verified:** GET route, `@provider_required`.
- **Connected to backend:** Yes. Flask builds notifications from pending appointments via `build_provider_notifications()`.

---

## 6. Frontend-to-Backend Communication

### Communication Patterns Found

**A. Traditional HTML Form POST (server-rendered, full page reload):**
- `register.html` → `/register` (POST)
- `login.html` → `/login` (POST)
- `provider_login.html` → `/provider-login` (POST, hardcoded URL)
- `provider_settings.html` → `/provider-settings` (POST, 3 forms with different `action` values)
- `patients_details.html` → various note/followup routes (POST, but with wrong route names — see Section 8)

**B. JavaScript `fetch()` API:**
- **Only one `fetch()` call found:** `settings.html` line ~2530 → `fetch("/settings/change-password", ...)` with JSON body (`current_password`, `new_password`).
- **Problems:** Endpoint `/settings/change-password` does not match Flask route `/change-password`. Flask returns HTML, not JSON, so `response.json()` will fail.

**C. JavaScript-only (no backend communication):**
- `appointments.html` — `bookAppointment()` stores in local array, hardcoded demo data
- `monitoring.html` — `saveReading()`, `saveWeight()`, `markTaken()` — client-side only
- `health records.html` — `viewRecord()`, `deleteRecord()` — client-side only
- `availability.html` — `saveSchedule()` — localStorage only
- `consultation.html` — forms with `method="POST"` but no `action`, handled by JavaScript

**D. `url_for()` template links (navigation only):**
- Many `<a href="{{ url_for('...') }}">` links for navigation between pages.
- Some reference routes or templates that don't exist (see Section 8).

**E. Session-based authentication:**
- Flask uses `session` cookie for patient (`logged_in`) and provider (`provider_logged_in`) auth. No token-based API auth.

**F. `localStorage`:**
- Used for theme/appearance settings (`script.js`, key: `ncdNepalSettings`).
- Used for availability schedule (`availability.html`).
- No evidence of `sessionStorage` use.

---

## 7. Forms and JavaScript-Only Features

### Forms That Submit to Flask (verified)

| Template | Form ID/Class | Action | Method | Fields |
|----------|--------------|--------|--------|--------|
| `register.html` | `registerForm` | `{{ url_for('register') }}` | POST | fullname, email, phone, date_of_birth, gender, address, account_type, password, confirm_password, terms |
| `login.html` | `loginForm` | `{{ url_for('login') }}` | POST | email, password |
| `provider_login.html` | (none) | `/provider-login` | POST | email, password |
| `provider_settings.html` | (3 forms) | `{{ url_for('provider_settings') }}` | POST | fullname, phone, organization; notification toggles; privacy toggles; current_password, new_password, confirm_password |
| `patients_details.html` | (note forms) | `url_for('add_patient_note', ...)` | POST | appointment_id, note |
| `patients_details.html` | (note forms) | `url_for('delete_patient_note', ...)` | POST | — |
| `patients_details.html` | (note forms) | `url_for('edit_patient_note', ...)` | POST | note |
| `patients_details.html` | (followup form) | `url_for('add_patient_followup', ...)` | POST | followup_date, followup_time, followup_type, notes |
| `follow_up.html` | (complete form) | `url_for('complete_patient_followup', ...)` | POST | — |

### JavaScript-Only Features (no backend call)

| Feature | Template | JS Functions | Backend Endpoint? |
|---------|----------|--------------|-------------------|
| Appointment booking | `appointments.html` | `bookAppointment()`, `updateDoctorList()`, `openRescheduleModal()`, `confirmReschedule()`, `cancelAppointment()` | **No** — local array only |
| Health monitoring readings | `monitoring.html` | `saveReading()`, `saveWeight()`, `markTaken()` | **No** — client-side only |
| Health records CRUD | `health records.html` | `viewRecord()`, `deleteRecord()`, `openAddRecordModal()` | **No** — client-side only |
| Availability schedule | `availability.html` | `saveSchedule()`, `copyMondayToWeekdays()`, `resetSchedule()`, `openExceptionModal()` | **No** — localStorage only |
| Consultation forms | `consultation.html` | `consultationForm`, `followupForm` | **No** — no action, JS-handled |

### Hardcoded Demo Data (verified — not from backend)

- `appointments.html`: `doctors` object with 4 services and demo providers (Dr. Anisha Sharma, Dr. Suman Thapa, Dr. Riya Karki, Nutrition Specialist). `appointments` array with 4 demo appointments.
- `script.js`: No demo data, only theme logic.

---

## 8. Identified Bugs and Inconsistencies

### Critical (will break the app)

**B1. Missing templates referenced by routes:**
- `/profile` → `profile.html` ❌ does not exist
- `/records` → `records.html` ❌ does not exist (actual: `health records.html`)
- `/change-password` → `change-password.html` ❌ does not exist

**B2. Route name mismatches (will cause `BuildError` on `url_for()`):**
- `patients_details.html` uses `add_patient_note` → Flask has `add_consultation_note`
- `patients_details.html` uses `delete_patient_note` → Flask has `delete_consultation_note`
- `patients_details.html` uses `edit_patient_note` → Flask has `edit_consultation_note`
- `patients_details.html` uses `add_patient_followup` → Flask has `add_followup`
- `patients_details.html` + `follow_up.html` use `complete_patient_followup` → Flask has `complete_followup`

**B3. Endpoint mismatch in `fetch()` call:**
- `settings.html` calls `fetch("/settings/change-password")` but Flask route is `/change-password`

**B4. Filename with space:**
- `health records.html` — unconventional, may cause issues with some web servers or tools.

### Major (features don't work as expected)

**B5. Appointment booking doesn't reach backend:**
- `appointments.html` `bookAppointment()` is pure JavaScript with hardcoded demo data. Flask's `/appointments` POST route is never called.

**B6. Health monitoring data not saved to backend:**
- `monitoring.html` uses client-side JavaScript only. No endpoint receives monitoring readings.

**B7. Health records not connected to backend:**
- `health records.html` uses client-side JavaScript only.

**B8. Availability not connected to backend:**
- `availability.html` stores schedule in `localStorage` only.

**B9. Settings password change will fail:**
- Wrong endpoint URL + Flask returns HTML not JSON → `response.json()` will throw.

**B10. `consultation.html` forms have no action:**
- `consultationForm` and `followupForm` have `method="POST"` but no `action`, handled by JavaScript only.

### Minor

**B11. Inconsistent static file paths:**
- Some templates reference `js/script.js`, others reference `script.js` (without `js/`).

**B12. Hardcoded demo data in frontend:**
- `appointments.html` has hardcoded doctors and appointments in JavaScript.

---

## 9. Security Concerns

**S1. Passwords stored in plain text:**
- `app.py` stores passwords in plain text in `app.config["registered_user"]` and `app.config["registered_provider"]`. No hashing (no `werkzeug.security` or similar).

**S2. In-memory data storage:**
- All data stored in Python lists/dictionaries in `app.config`. Data is lost on server restart. No persistence, no database.

**S3. No CSRF protection visible:**
- Flask-WTF or CSRF tokens not observed in forms.

**S4. Secret key is hardcoded:**
- `app.secret_key = "ncd-nepal-secret-key"` — hardcoded in source.

**S5. Session-based auth only:**
- No token-based (JWT) authentication. Sessions are cookie-based.

**S6. Hardcoded provider login URL:**
- `provider_login.html` uses `action="/provider-login"` instead of `url_for()`, which is brittle if URL structure changes.

---

## 10. Candidate Backend Capabilities and Data Models

**These are recommendations based on frontend requirements, not implemented code.**

### Authentication
- Patient register/login/logout
- Provider register/login/logout
- Password change (with validation: min 8 chars, match confirmation, different from current)
- Password hashing (bcrypt/argon2 — never plain text)

### Patient Endpoints
- `POST /api/patients/register/` — fullname, email, phone, date_of_birth, gender, address, account_type, password
- `POST /api/patients/login/` — email, password → returns token/session
- `GET /api/patients/profile/` — read patient profile
- `PUT /api/patients/settings/` — update fullname, phone, address
- `POST /api/patients/change-password/` — current_password, new_password, confirm_password
- `GET /api/patients/dashboard/` — dashboard summary data

### Health Monitoring
- `POST /api/patients/monitoring/` — save blood pressure, glucose, weight readings
- `GET /api/patients/monitoring/` — list readings
- `POST /api/patients/monitoring/medication/` — mark medication as taken

### Appointments
- `GET /api/patients/appointments/` — list patient's appointments
- `POST /api/patients/appointments/` — book appointment (service, provider, date, time, type, location, reason)
- `PUT/PATCH /api/patients/appointments/<id>/` — reschedule/cancel

### Health Records
- `GET /api/patients/records/` — list health records
- `POST /api/patients/records/` — add record
- `DELETE /api/patients/records/<id>/` — delete record

### Notifications
- `GET /api/patients/notifications/` — patient notifications
- `GET /api/providers/notifications/` — provider notifications

### Provider Endpoints
- `POST /api/providers/register/`
- `POST /api/providers/login/`
- `GET /api/providers/dashboard/` — stats + patient list
- `GET /api/providers/appointments/` — provider's appointments
- `POST /api/providers/appointments/<id>/<action>/` — confirm/reject/cancel/complete
- `GET /api/providers/patients/` — patient list
- `GET /api/providers/patients/<id>/` — patient details
- `POST /api/providers/patients/<id>/notes/` — add consultation note
- `PUT /api/providers/patients/<id>/notes/<note_id>/` — edit note
- `DELETE /api/providers/patients/<id>/notes/<note_id>/` — delete note
- `POST /api/providers/patients/<id>/followups/` — add follow-up
- `POST /api/providers/patients/<id>/followups/<id>/complete/` — mark complete
- `GET /api/providers/settings/` — settings
- `PUT /api/providers/settings/` — update settings

### Availability
- `GET /api/providers/availability/` — get schedule
- `PUT /api/providers/availability/` — save schedule

### Candidate Data Models

| Model | Fields |
|-------|--------|
| Patient | id, fullname, email, phone, date_of_birth, gender, address, account_type, password_hash, created_at |
| Provider | id, fullname, email, phone, provider_type, specialization, organization, location, password_hash, created_at |
| Appointment | id, patient, provider, appointment_date, appointment_time, consultation_type, condition, reason, status, created_at, updated_at, notification, action_by, action_at |
| HealthRecord | id, patient, type, value, date, notes, created_at |
| ConsultationNote | id, patient, provider, note, created_at, updated_at |
| FollowUp | id, patient, provider, followup_date, followup_time, followup_type, notes, status, created_at, completed_at |
| ProviderSettings | id, appointment_notifications, patient_notifications, followup_notifications, system_notifications, profile_visible, organization_visible |

---

## 11. Remaining Questions and Items Requiring Verification

**V1.** Does `provider_register.html` form use `action="{{ url_for('provider_register') }}"`? (Not yet verified — form action not inspected.)

**V2.** Does `settings.html` account settings form (non-password) submit to `{{ url_for('settings') }}`? Form action not fully inspected.

**V3.** Does `consultation.html` have any JavaScript that submits `consultationForm` or `followupForm` to a backend endpoint? Forms have no `action` attribute.

**V4.** Does `notifications.html` use the `data-appointments-url` attribute anywhere in JavaScript? No fetch call found using it.

**V5.** Are there any other `fetch()` or AJAX calls in templates not yet discovered? Only one `fetch()` was found (in `settings.html`).

**V6.** What is the intended behavior when `/profile`, `/records`, or `/change-password` are visited? Templates are missing — need to determine if these pages should be created or routes removed.

**V7.** Is `health records.html` the intended filename, or should it be renamed to `records.html` to match the route?

**V8.** Are the hardcoded demo doctors/appointments in `appointments.html` meant to be replaced by backend data? (Likely yes, but not confirmed.)

**V9.** Does the frontend expect JSON API responses or HTML template rendering? Mixed — some forms POST and get HTML, one `fetch()` expects JSON.

---

## 12. Recommended Next Development Task

**Immediate priority (before building Django REST Framework backend):**

1. **Fix the Flask frontend bugs** so existing routes work:
   - Create missing templates: `profile.html`, `records.html` (or rename `health records.html`), `change-password.html`.
   - Fix route name mismatches in `patients_details.html` and `follow_up.html` (`add_patient_note` → `add_consultation_note`, etc.).
   - Fix `settings.html` fetch endpoint (`/settings/change-password` → `/change-password`) and handle HTML vs JSON response.

2. **Then** build Django REST Framework backend with the candidate endpoints and data models in Section 10, and update frontend forms to submit to the new API instead of the Flask routes.

**Do not modify any existing project files during this investigation phase.** This document is for reference only.

---

**File location:** `E:\Desktop\ncd-frontend\ncd\docs\FRONTEND_AUDIT.md`  
**This file is the single source of truth for frontend audit findings.** Future AI sessions should read this file before continuing work on the backend.