"""Examination hall management routes blueprint (Phase 3)."""

from flask import Blueprint

from app.routes.dashboard import render_module_placeholder
from app.services.auth_service import admin_required

halls_bp = Blueprint("halls", __name__, url_prefix="/halls")


@halls_bp.get("/")
@admin_required
def index():
    """Protected placeholder until Phase 3 hall management is implemented."""
    return render_module_placeholder(
        module_name="Examination Halls",
        phase_label="Phase 3",
        description="Examination hall creation, row/column dimensions, and capacity management will be implemented in Phase 3.",
        active_nav="halls",
    )
