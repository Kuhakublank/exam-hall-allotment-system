"""Examination session and registration routes blueprint (Phase 5)."""

from flask import Blueprint

from app.routes.dashboard import render_module_placeholder
from app.services.auth_service import admin_required

exams_bp = Blueprint("exams", __name__, url_prefix="/exams")


@exams_bp.get("/")
@admin_required
def index():
    """Protected placeholder until Phase 5 examination management is implemented."""
    return render_module_placeholder(
        module_name="Examination Sessions",
        phase_label="Phase 5",
        description="Multi-subject exam sessions and student registrations will be implemented in Phase 5.",
        active_nav="exams",
    )
