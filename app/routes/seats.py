"""Seat layout configuration routes (blocked and accessible seats — Phase 3)."""

from flask import Blueprint

from app.routes.dashboard import render_module_placeholder
from app.services.auth_service import admin_required

seats_bp = Blueprint("seats", __name__, url_prefix="/seats")


@seats_bp.get("/")
@admin_required
def index():
    """Protected placeholder until Phase 3 seat layout management is implemented."""
    return render_module_placeholder(
        module_name="Seat Management",
        phase_label="Phase 3",
        description="Interactive hall seat grid configuration (blocked and accessible seats) will be implemented in Phase 3.",
        active_nav="seats",
    )
