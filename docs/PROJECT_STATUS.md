# NCD Platform — Project Status

Updated: 2026-11-21

## Project

A Flask and PostgreSQL digital health platform for NCD monitoring, appointment booking, and patient-provider care coordination.

## Structure

- `backend/` — Flask application, SQLAlchemy models, dependencies, and migrations.
- `frontend/` — Jinja templates, CSS, and JavaScript.
- `docs/` — Requirements, frontend audit, and this status file.
- `run.py` — Starts the app from the project root.
- `.env` — Local configuration only; ignored by Git.

## Completed MVP

- Patient/provider authentication and role-based routes.
- Database-backed appointments, health readings and records, medication logs, consultation notes, follow-ups, availability, and provider settings.
- Patient notification preferences and patient-owned health-record deletion.
- Manual acceptance with isolated synthetic data confirmed that a submitted appointment survives refresh and a synthetic record can be deleted. The temporary QA database was removed.
- Database migrations are applied to PostgreSQL: `b7c4d2e91a63`, `c39a70f2d841`, `1d6e8c3f4a20`, `2f8c1a6d4e90`, `7a4c9e2d6b31`.
- Reorganized app passed route, static asset, and migration discovery checks from this path using isolated SQLite.

## Notes

- Refreshing an unsubmitted appointment form clears the draft; bookings persist after submission.
- Do not use real patient data for testing. Keep `.env` out of Git.
- The original open workspace remains as a backup because Windows blocked moving its locked root. The separate `E:\Desktop\NCD-Platform` Django/React repository is untouched.

## Optional Future Features

Password reset, broader CSRF protection, dynamic prevention/community content, patient-list search/filter, and health-record or appointment export.

## Next Task

No required MVP work remains. Use `E:\Desktop\NCD-Project` as the working project path. Choose an optional future feature only if development continues.
