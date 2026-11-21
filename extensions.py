from flask_sqlalchemy import SQLAlchemy


# Shared SQLAlchemy extension. The app configures it in app.py, while
# models.py imports it without importing the Flask application itself.
db = SQLAlchemy()
