"""Authentication and administrator access control service."""

from functools import wraps
from urllib.parse import urljoin, urlparse
from flask import abort, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.models.user import User


def normalize_email(email: str | None) -> str:
    """Normalize an email address for consistent lookup and storage."""
    return (email or "").strip().lower()


def authenticate_admin(email: str, password: str) -> User | None:
    """Verify email and password for an active administrator account.

    Returns the User on success or None on any failure without revealing
    whether the email address exists.
    """
    normalized_email = normalize_email(email)
    if not normalized_email or not password:
        return None

    user = User.query.filter(func.lower(User.email) == normalized_email).first()
    if user is None:
        return None
    if not user.is_active or user.role != "admin":
        return None
    if not user.check_password(password):
        return None
    return user


def create_admin_user(username: str, email: str, password: str) -> User:
    """Create and persist a new administrator user with a hashed password.

    Raises ValueError if inputs are invalid or an account already exists.
    """
    clean_username = (username or "").strip()
    clean_email = normalize_email(email)

    if not clean_username:
        raise ValueError("Administrator username is required.")
    if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        raise ValueError("A valid administrator email address is required.")
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    existing_email = User.query.filter(func.lower(User.email) == clean_email).first()
    if existing_email is not None:
        raise ValueError(f"An account with email '{clean_email}' already exists.")

    existing_username = User.query.filter(
        func.lower(User.username) == clean_username.lower()
    ).first()
    if existing_username is not None:
        raise ValueError(f"An account with username '{clean_username}' already exists.")

    admin = User(
        username=clean_username,
        email=clean_email,
        role="admin",
        is_active=True,
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    return admin


def admin_required(view_func):
    """Protect a route so only authenticated active administrators can access it."""

    @wraps(view_func)
    @login_required
    def wrapped_view(*args, **kwargs):
        if not current_user.is_active or getattr(current_user, "role", None) != "admin":
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped_view


def is_safe_redirect_url(target: str | None) -> bool:
    """Return True only when target points back to the same host safely."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc
