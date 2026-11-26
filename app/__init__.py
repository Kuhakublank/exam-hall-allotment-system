"""Flask application factory."""

import os
from flask import Flask, render_template
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.cli import register_cli_commands
from app.config import config_by_name
from app.extensions import csrf, db, login_manager, migrate


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
    login_manager.init_app(flask_app)
    csrf.init_app(flask_app)

    with flask_app.app_context():
        event.listen(Engine, "connect", _enable_sqlite_foreign_keys)

    # Import models so SQLAlchemy & Flask-Migrate register all tables
    from app.models.user import User
    import app.models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id: str):
        """Reload the authenticated user object from the session user ID."""
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    from app.routes import (
        allocations_bp,
        auth_bp,
        constraints_bp,
        dashboard_bp,
        exams_bp,
        halls_bp,
        health_bp,
        reports_bp,
        seats_bp,
        students_bp,
        subjects_bp,
    )

    for blueprint in (
        health_bp,
        auth_bp,
        dashboard_bp,
        students_bp,
        subjects_bp,
        exams_bp,
        halls_bp,
        seats_bp,
        constraints_bp,
        allocations_bp,
        reports_bp,
    ):
        flask_app.register_blueprint(blueprint)

    register_cli_commands(flask_app)

    @flask_app.errorhandler(413)
    def request_entity_too_large(_error):
        """Return a user-friendly HTTP 413 page when an upload exceeds MAX_CONTENT_LENGTH."""
        max_bytes = flask_app.config.get("MAX_CONTENT_LENGTH") or (5 * 1024 * 1024)
        max_mb = max(1, round(max_bytes / (1024 * 1024)))
        return render_template("errors/413.html", max_mb=max_mb), 413

    return flask_app
