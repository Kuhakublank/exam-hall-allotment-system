"""Flask Blueprints package."""

from flask import Blueprint, jsonify

from app.routes.allocations import allocations_bp
from app.routes.auth import auth_bp
from app.routes.constraints import constraints_bp
from app.routes.dashboard import dashboard_bp
from app.routes.exams import exams_bp
from app.routes.halls import halls_bp
from app.routes.reports import reports_bp
from app.routes.seats import seats_bp
from app.routes.students import students_bp
from app.routes.subjects import subjects_bp

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """Return a minimal health response confirming the Flask app is running."""
    return jsonify({"status": "ok"}), 200


__all__ = [
    "health_bp",
    "auth_bp",
    "dashboard_bp",
    "students_bp",
    "subjects_bp",
    "exams_bp",
    "halls_bp",
    "seats_bp",
    "constraints_bp",
    "allocations_bp",
    "reports_bp",
]
