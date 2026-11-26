"""Subject management routes blueprint (Phase 5)."""

from flask import Blueprint

from app.routes.dashboard import render_module_placeholder
from app.services.auth_service import admin_required

subjects_bp = Blueprint("subjects", __name__, url_prefix="/subjects")


@subjects_bp.get("/")
@admin_required
def index():
    """Protected placeholder until Phase 5 subject management is implemented."""
    return render_module_placeholder(
        module_name="Subject Management",
        phase_label="Phase 5",
        description="Subject creation and code management will be implemented in Phase 5.",
        active_nav="subjects",
    )
