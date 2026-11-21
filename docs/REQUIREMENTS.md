# NCD Platform — Requirements

### 1. Project Purpose

The NCD Platform is a digital health platform for non-communicable disease (NCD) awareness, prevention, monitoring, and continuity of care. It enables patients to manage their health and connect with healthcare service providers, while giving providers tools to manage appointments, patient records, consultation notes, and follow-ups.

The intended users are:

- **Patients** — individuals who need to monitor NCDs (e.g., diabetes, blood pressure, thyroid), book appointments with providers, view health records, and receive notifications.
- **Healthcare Service Providers** — doctors and health workers who register, manage their availability, view patient lists, record consultation notes, track follow-ups, and update appointment statuses.

## 2. User Roles

### Patient
A registered patient can:
- Create an account and log in.
- View and update their profile and account settings.
- Book, view, reschedule, and cancel appointments with providers.
- Record and view health monitoring readings (blood pressure, glucose, weight).
- View health records.
- Receive notifications about appointment status changes.
- Change their password.

### Healthcare Service Provider
A registered provider can:
- Create an account and log in.
- View and update their profile and account settings.
- View a dashboard with appointment statistics and patient lists.
- View patient details, appointment history, consultation notes, and follow-ups.
- Add, edit, and delete consultation notes for patients.
- Add and complete patient follow-ups.
- Manage their availability schedule.
- Confirm, reject, cancel, or complete appointment requests from patients.
- Receive notifications about new appointments and status changes.

## 3. Patient Requirements

The following requirements are based on the existing frontend (verified where noted) and planned backend functionality.

### 3.1 Registration and Login
- **Confirmed:** The frontend `register.html` collects fullname, email, phone, date_of_birth, gender, address, account_type, password, confirm_password, and terms acceptance. The form submits to `/register` (POST).
- **Confirmed:** The frontend `login.html` collects email and password. The form submits to `/login` (POST).
- **Requirement:** The backend must validate all required fields, check password match, hash passwords with Werkzeug, and create a patient account. On successful login, the backend must establish a session and redirect to the patient dashboard.
- **Requirement:** Duplicate email registration must be rejected.

### 3.2 Patient Profile
- **Confirmed:** The frontend expects a `/profile` route, but `profile.html` does not currently exist (verified in FRONTEND_AUDIT.md).
- **Requirement:** The backend must provide a patient profile page showing fullname, email, phone, date_of_birth, gender, address, and account_type. The missing `profile.html` template must be created or the route removed.

### 3.3 Dashboard
- **Confirmed:** The `/dashboard` route exists and requires patient login. It renders `dashboard.html` with the user's fullname from the session.
- **Requirement:** The dashboard must serve as the patient's home page with navigation to monitoring, prevention, community, appointments, records, notifications, settings, profile, and logout.

### 3.4 Health Monitoring
- **Confirmed:** The frontend `monitoring.html` allows patients to record/view blood pressure, glucose, and weight readings, and mark medications as taken. Currently, this is client-side only — no backend endpoint receives the data (verified in FRONTEND_AUDIT.md).
- **Requirement:** The backend must provide endpoints to save and retrieve health monitoring readings per patient. This is proposed functionality, not yet implemented.

### 3.5 Health Records
- **Confirmed:** The frontend `health records.html` allows viewing and deleting health records. Currently client-side only. The route `/references `records.html` which does not exist; the actual file is `health records.html` (verified in FRONTEND_AUDIT.md).
- **Requirement:** The backend must provide endpoints to create, view, and delete health records per patient. The missing `records.html` template must be created or the route/filename aligned.

### 3.6 Appointment Booking and Cancellation
- **Confirmed:** The frontend `appointments.html` collects service, provider, date, time, type, location, and reason for booking. Currently, `bookAppointment()` stores data in a local JavaScript array with hardcoded demo data — it never calls the backend (verified in FRONTEND_AUDIT.md).
- **Requirement:** The backend must provide an endpoint to create appointments and store them persistently. The frontend booking form must be updated to submit to the backend instead of using client-side-only storage.
- **Requirement:** Patients must be able to view their own appointments and cancel them.

### 3.7 Notifications
- **Confirmed:** The `/notifications` route exists and requires patient login. The backend builds notifications from appointment data (verified in FRONTEND_AUDIT.md).
- **Requirement:** Patients must receive notifications when their appointment status changes (pending, confirmed, rejected, cancelled, completed).

### 3.8 Other Patient Features
- **Settings:** The `/settings` route allows updating fullname, phone, and address (POST form) and changing password (JavaScript `fetch` call). Currently has an endpoint mismatch (`/settings/change-password` vs `/change-password`).
- **Change Password:** The `/change-password` route exists but `change-password.html` template is missing. Requires backend validation (current password correct, new password at least 8 characters, confirmation match).
- **Prevention/Community:** The `/prevention` and `/community` routes exist and render static educational pages. No backend data required for MVP.

## 4. Service Provider Requirements

### 4.1 Provider Registration and Login
- **Confirmed:** The frontend `provider_register.html` collects fullname, email, phone, provider_type, specialization, organization, location, password, confirm_password. The frontend `provider_login.html` collects email and password and submits to `/provider-login` (POST, hardcoded URL).
- **Requirement:** The backend must validate all required fields, hash passwords with Werkzeug, create a provider account, and establish a provider session on login.

### 4.2 Provider Profile
- **Confirmed:** The `/provider-profile` route exists and renders `provider_profile.html` with session data (fullname, email, phone, provider_type, specialization, organization, location).
- **Requirement:** Providers must be able to view their profile details.

### 4.3 Dashboard
- **Confirmed:** The `/service-provider` route exists and requires provider login. It shows appointment counts (total, pending, confirmed, completed) and a patient list.
- **Requirement:** The provider dashboard must display appointment statistics and a list of the provider's patients.

### 4.4 Patient Management
- **Confirmed:** The `/patients` route lists a provider's patients with appointment history. The `/patients/<patient_id>` route shows patient details including notes and follow-ups.
- **Requirement:** Providers must be able to view their patient list, search/filter patients, and view individual patient details with appointment history.

### 4.5 Appointment Management
- **Confirmed:** The `/provider-appointments` route lists a provider's appointments. The `/provider-appointments/<int:id>/<action>` route allows confirming, rejecting, cancelling, or completing appointments (actions: confirm, reject, cancel, complete).
- **Requirement:** Providers must be able to view all appointment requests and update each appointment's status. Only the owning provider may modify an appointment's status.

### 4.6 Consultation Notes
- **Confirmed:** The frontend `patients_details.html` has forms for adding, editing, and deleting consultation notes. However, the `url_for()` calls reference route names that do not exist in `app.py` (e.g., `add_patient_note` vs actual `add_consultation_note`) — verified mismatch in FRONTEND_AUDIT.md.
- **Requirement:** Providers must be able to add, edit, and delete consultation notes for their patients. Route names in templates must match backend route function names.

### 4.7 Patient Follow-ups
- **Confirmed:** The frontend has forms for adding follow-ups and marking them complete. Route name mismatches exist (e.g., `add_patient_followup` vs actual `add_followup`).
- **Requirement:** Providers must be able to add follow-ups for patients and mark follow-ups as completed.

### 4.8 Availability Management
- **Confirmed:** The `/availability` route exists and requires provider login. Currently, the schedule is stored in browser `localStorage` only — no backend endpoint receives it (verified in FRONTEND_AUDIT.md).
- **Requirement:** Providers must be able to set and save their weekly availability schedule. The backend must persist availability data. This is proposed functionality for MVP.

### 4.9 Notifications and Settings
- **Confirmed:** The `/provider-notifications` route builds notifications from pending appointments. The `/provider-settings` route handles account preferences, notification settings, privacy settings, and password change via three POST forms.
- **Requirement:** Providers must receive notifications for new appointment requests and status changes. Providers must be able to configure notification preferences and privacy settings.

## 5. Appointment Workflow

### 5.1 Appointment States
An appointment can be in one of the following states:

| State | Meaning | Who can set it |
|-------|---------|----------------|
| Pending | Appointment requested, awaiting provider action | Patient (on booking) |
| Confirmed | Provider has accepted the appointment | Provider only |
| Rejected | Provider has declined the appointment | Provider only |
| Cancelled | Appointment cancelled | Patient or Provider |
| Completed | Appointment has been completed | Provider only |

### 5.2 Appointment Lifecycle

1. **Patient books an appointment** — status is set to `Pending`.
2. **Provider reviews the request** — provider can `Confirm`, `Reject`, or `Cancel`.
3. **If Confirmed** — the appointment proceeds; patient receives a confirmation notification.
4. **If Rejected or Cancelled** — patient receives a notification.
5. **After the appointment occurs** — provider can mark it `Completed`.

### 5.3 Access Control
- Patients can only book, view, and cancel their own appointments.
- Providers can only confirm, reject, cancel, or complete appointments that belong to them.
- Patients cannot change an appointment to `Confirmed` or `Completed`.

## 6. Data Requirements

The system needs to store the following information. This section identifies data needs only; database table design is not included here.

### 6.1 Patients
- Unique identifier
- Full name
- Email address (unique)
- Phone number
- Date of birth
- Gender
- Address
- Account type
- Password hash (never plain text)
- Account creation timestamp

### 6.2 Providers
- Unique identifier
- Full name
- Email address (unique)
- Phone number
- Provider type
- Specialization
- Organization
- Location
- Password hash (never plain text)
- Account creation timestamp

### 6.3 Appointments
- Unique identifier
- Patient reference
- Provider reference
- Appointment date
- Appointment time
- Consultation type
- Condition/reason for visit
- Status (Pending, Confirmed, Rejected, Cancelled, Completed)
- Creation timestamp
- Last update timestamp
- Notification message
- Who performed the last action and when

### 6.4 Health Records
- Unique identifier
- Patient reference
- Record type (e.g., blood pressure, glucose, weight)
- Value
- Date recorded
- Notes
- Creation timestamp

### 6.5 Consultation Notes
- Unique identifier
- Patient reference
- Provider reference
- Note text
- Creation timestamp
- Last update timestamp

### 6.6 Follow-ups
- Unique identifier
- Patient reference
- Provider reference
- Follow-up date
- Follow-up time
- Follow-up type
- Notes
- Status (Pending, Completed)
- Creation timestamp
- Completion timestamp

### 6.7 Provider Settings
- Provider reference
- Appointment notifications (on/off)
- Patient notifications (on/off)
- Follow-up notifications (on/off)
- System notifications (on/off)
- Profile visible (on/off)
- Organization visible (on/off)

## 7. Security Requirements

### 7.1 Secure Password Hashing
- Passwords must never be stored in plain text.
- Use Werkzeug (`generate_password_hash`, `check_password_hash`) for password hashing and verification.

### 7.2 Role-Based Access
- Patient routes require patient authentication (`session["logged_in"]`).
- Provider routes require provider authentication (`session["provider_logged_in"]`).
- Patients must not access provider-only routes and vice versa.
- Providers must only access their own patients' data and their own appointments.

### 7.3 Protected Patient Information
- Health data (monitoring readings, records, consultation notes, follow-ups) must be accessible only to the patient and their assigned providers.
- No patient data should be exposed to unauthorized users.

### 7.4 Input Validation
- All form inputs must be validated on the server side (required fields, email format, password length, date formats).
- Passwords must be at least 8 characters.
- Password confirmation must match the new password.
- New password must differ from current password.

### 7.5 Secure Session Handling
- Use Flask session-based authentication with a strong, non-hardcoded secret key.
- Sessions must be cleared on logout.
- Login failures must not reveal whether the email exists.

### 7.6 Protection Against Unauthorized Access
- Routes requiring authentication must redirect unauthenticated users to the appropriate login page.
- Providers must not be able to access or modify other providers' appointments or patients.
- No sensitive data (passwords, secret keys) in source code or logs.

## 8. Non-Functional Requirements

### 8.1 Usability
- The existing HTML/CSS/JavaScript frontend must continue to work with minimal changes.
- Navigation between pages must be clear and consistent.
- Forms must provide clear error messages for invalid input.

### 8.2 Reliability
- Data must persist across server restarts (PostgreSQL database).
- Failed login or form submission must not corrupt existing data.

### 8.3 Maintainability
- Code must be organized and documented for a beginner developer.
- Configuration (secret key, database URI) must not be hardcoded in source files.
- Route names in templates must match backend route function names.

### 8.4 Data Persistence
- All user accounts, appointments, health records, consultation notes, and follow-ups must be stored in PostgreSQL.
- No data loss on server restart.

## 9. MVP Scope and Priorities (November 22 Deadline)

### Essential for First Working Version
- Patient registration and login with hashed passwords.
- Provider registration and login with hashed passwords.
- Patient dashboard with navigation.
- Provider dashboard with appointment statistics and patient list.
- Patient appointment booking (submitted to backend, stored in PostgreSQL).
- Provider appointment management (confirm, reject, cancel, complete).
- Patient view of their own appointments.
- Provider patient list and patient detail view.
- Session-based authentication with role-based access control.
- PostgreSQL persistent storage via SQLAlchemy.

### Important but Can Follow After MVP
- Health monitoring readings (backend endpoints to save/retrieve).
- Health records (backend endpoints to create/view/delete).
- Patient notifications (appointment status changes).
- Provider notifications (new appointment requests).
- Provider availability management (persisted to database).
- Patient profile page (`profile.html` template creation).
- Patient health records page (`records.html` template creation or alignment).
- Patient change-password page (`change-password.html` template creation).
- Provider consultation notes (add, edit, delete).
- Provider patient follow-ups (add, complete).
- Patient settings (update fullname, phone, address).
- Provider settings (preferences, notifications, privacy).

### Optional / Future Improvements
- Password reset flow (email-based).
- CSRF protection (Flask-WTF).
- Token-based (JWT) authentication in addition to session-based.
- Prevention and community pages with dynamic content.
- Responsive design improvements.
- Search and filtering for patient lists.
- Export of health records or appointment history.

---

## 10. Current Implementation Review (November 21, 2026)

The Essential for First Working Version list and the Important but Can Follow After MVP list above are implemented in the current Flask application. Patient and provider workflows use SQLAlchemy persistence, including appointment submissions, health readings and records, consultation notes, follow-ups, provider availability, and account settings. Patient health record deletion is restricted to records owned by the signed-in patient. The main remaining MVP task is manual browser acceptance using test-only accounts; isolated SQLite route checks have passed for the relevant save, reload, and ownership flows.

Manual acceptance using isolated SQLite test accounts is complete: a submitted appointment remained visible after refresh, and the synthetic health record was deleted. No real patient/provider data was used. The following items remain optional future improvements rather than MVP blockers: password reset, broader CSRF protection, dynamic prevention/community content, patient-list search/filtering, and data export. Appointment fees are display estimates; payment processing is not implemented.

**File location:** `E:\Desktop\ncd-frontend\ncd\docs\REQUIREMENTS.md`
**Source references:** `docs/FRONTEND_AUDIT.md` (verified frontend findings), existing `app.py`, HTML templates.
