"""Pytest fixtures for isolated application and database testing."""

import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    """Create a Flask app configured for isolated testing."""
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db_session(app):
    """Provide the active SQLAlchemy session for database tests."""
    return _db.session


@pytest.fixture()
def client(app):
    """Provide a Flask test client."""
    return app.test_client()
