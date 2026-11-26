"""Flask application factory."""

import os
from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.config import config_by_name
from app.extensions import db, migrate


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """Ensure SQLite enforces foreign keys during isolated unit tests."""
    module_name = type(dbapi_connection).__module__
    if module_name.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application instance."""
    resolved_name = config_name or os.environ.get("FLASK_ENV", "development")
    config_cls = config_by_name.get(resolved_name, config_by_name["development"])

    flask_app = Flask(__name__)
    flask_app.config.from_object(config_cls)

    if not flask_app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError(
            "DATABASE_URL is not configured. Copy .env.example to .env and set DATABASE_URL."
        )

    db.init_app(flask_app)
    migrate.init_app(flask_app, db)

    with flask_app.app_context():
        event.listen(Engine, "connect", _enable_sqlite_foreign_keys)

    # Import models so SQLAlchemy & Flask-Migrate register all tables
    import app.models  # noqa: F401
    from app.routes import health_bp

    flask_app.register_blueprint(health_bp)

    return flask_app
