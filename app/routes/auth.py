"""Authentication routes blueprint (login, logout, access control — Phase 2)."""

from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
