"""Constraint configuration routes blueprint (Phase 5)."""

from flask import Blueprint

from app.routes.dashboard import render_module_placeholder
from app.services.auth_service import admin_required

constraints_bp = Blueprint("constraints", __name__, url_prefix="/constraints")


@constraints_bp.get("/")
@admin_required
def index():
    """Protected placeholder until Phase 5 constraint configuration is implemented."""
    return render_module_placeholder(
        module_name="Constraint Management",
        phase_label="Phase 5",
        description="Separation rules (same subject, same configured group), accessibility options, and solver limits will be configured in Phase 5.",
        active_nav="constraints",
    )
