"""Hall allotment and seating arrangement execution routes blueprint (Phase 9)."""

from flask import Blueprint

allocations_bp = Blueprint("allocations", __name__, url_prefix="/allocations")
