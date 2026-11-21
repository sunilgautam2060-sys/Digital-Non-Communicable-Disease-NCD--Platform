# NCD Platform

A Flask and PostgreSQL platform for NCD health monitoring, appointment booking, and patient-provider care coordination.

## Project layout

- `backend/` — Flask application, SQLAlchemy models, and database migrations.
- `frontend/` — Flask templates, CSS, and JavaScript assets.
- `docs/` — Requirements, frontend audit, and project status.
- `run.py` — Local application entry point.
- `.env` — Local secrets and database URL; never commit this file.

## Local setup

From the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

If `.env` already exists, keep it and do not overwrite it. Set `SECRET_KEY` and `DATABASE_URL` in `.env` using your local configuration. Do not put real credentials in GitHub.

Apply database migrations and start the local server:

```powershell
flask --app backend.app db upgrade
python run.py
```

The development server runs at `http://127.0.0.1:5000/`.

## Documentation

- [Project status](docs/PROJECT_STATUS.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Frontend audit](docs/FRONTEND_AUDIT.md)

Use fictional data for testing. Do not use real patient information in development or verification.
