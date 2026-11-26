"""Hall-wise reports, student lookup, and algorithm comparison routes blueprint (Phase 9)."""

from flask import Blueprint

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")
