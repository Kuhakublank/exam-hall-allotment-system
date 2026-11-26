"""Student management and CSV/XLSX import routes blueprint (Phase 4)."""

from flask import Blueprint

students_bp = Blueprint("students", __name__, url_prefix="/students")
