# NCD Platform — AI Development Instructions

## 1. Start of Every Session

- Read `docs/PROJECT_STATUS.md` before doing any work.
- Read `docs/FRONTEND_AUDIT.md` only when specific frontend details are needed.
- Check the actual source code before relying on documented assumptions.

## 2. Project Technology

- **Backend:** Flask
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Password hashing:** Werkzeug
- **Frontend:** Existing Flask templates, HTML, CSS and JavaScript.

## 2.1 Project Layout

- `backend/` contains the Flask application, SQLAlchemy models, dependencies, and migrations.
- `frontend/` contains the Flask templates and static CSS/JavaScript assets.
- `docs/` contains project status, requirements, and the frontend audit.
- `run.py` starts the local application from the project root.

## 3. Development Rules

- Assume the project owner is a beginner.
- Explain the current concept before making changes.
- Work on one small task at a time.
- Do not rewrite unrelated files.
- Do not replace existing functionality without explaining why.
- Never expose passwords, database credentials or secret keys.
- Never store passwords in plain text.
- Verify changes with appropriate tests.

## 4. Progress Documentation

After every meaningful, successfully verified milestone:

- Update `docs/PROJECT_STATUS.md`.
- Record completed work.
- Record unfinished work and known problems.
- Record important technical decisions.
- Write the exact next task.
- Never claim untested functionality is complete.

## 5. Session Handoff

- Never assume previous AI conversation history is available.
- Use `PROJECT_STATUS.md` to understand progress.
- Ask before making major architectural changes.
- Keep documentation concise.
