"""Hall allotment, seating arrangement, and validation routes blueprint (Phases 6–9)."""

from flask import Blueprint

from app.routes.dashboard import render_module_placeholder
from app.services.auth_service import admin_required

allocations_bp = Blueprint("allocations", __name__, url_prefix="/allocations")


@allocations_bp.get("/halls")
@admin_required
def hall_allotment():
    """Protected placeholder until Phase 6/9 FFD hall allotment integration."""
    return render_module_placeholder(
        module_name="Hall Allocation",
        phase_label="Phases 6 & 9",
        description="First-Fit Decreasing (FFD) hall allotment and capacity verification will be integrated here.",
        active_nav="hall_allocation",
    )


@allocations_bp.get("/seating")
@admin_required
def seating():
    """Protected placeholder until Phase 7/9 seating arrangement integration."""
    return render_module_placeholder(
        module_name="Seating Arrangement",
        phase_label="Phases 7 & 9",
        description="Backtracking (MRV + Forward Checking) and Greedy First-Fit baseline comparison will be integrated here.",
        active_nav="seating_arrangement",
    )


@allocations_bp.get("/validation")
@admin_required
def validation():
    """Protected placeholder until Phase 8/9 validation integration."""
    return render_module_placeholder(
        module_name="Validation & Conflict Checker",
        phase_label="Phases 8 & 9",
        description="Independent constraint verification, conflict detection, and optional OR-Tools CP-SAT checks will be integrated here.",
        active_nav="validation",
    )
