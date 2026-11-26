"""Hall-wise reports, student lookup, and algorithm comparison routes blueprint (Phase 9)."""

from flask import Blueprint

from app.routes.dashboard import render_module_placeholder
from app.services.auth_service import admin_required

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.get("/")
@admin_required
def index():
    """Protected placeholder until Phase 9 reporting is implemented."""
    return render_module_placeholder(
        module_name="Reports",
        phase_label="Phase 9",
        description="Hall-wise seating charts, student lookup lists, printable views, and PDF reports will be implemented in Phase 9.",
        active_nav="reports",
    )
