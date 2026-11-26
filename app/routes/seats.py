"""Seat layout configuration routes (blocked and accessible seats — Phase 3)."""

from flask import Blueprint

seats_bp = Blueprint("seats", __name__, url_prefix="/seats")
