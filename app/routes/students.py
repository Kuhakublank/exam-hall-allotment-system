"""Student management and CSV/XLSX import routes blueprint (Phase 4)."""

from flask import Blueprint

from app.routes.dashboard import render_module_placeholder
from app.services.auth_service import admin_required

students_bp = Blueprint("students", __name__, url_prefix="/students")


@students_bp.get("/")
@admin_required
def index():
    """Protected placeholder until Phase 4 student management is implemented."""
    return render_module_placeholder(
        module_name="Student Management",
        phase_label="Phase 4",
        description="Student CRUD records and CSV/XLSX import (Pandas & OpenPyXL) will be implemented in Phase 4.",
        active_nav="students",
    )
