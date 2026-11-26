"""Seat layout configuration routes (blocked and accessible seats)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Hall, Seat
from app.services.auth_service import admin_required
from app.services.hall_service import (
    get_hall_seat_matrix,
    toggle_seat_accessible,
    toggle_seat_blocked,
)

seats_bp = Blueprint("seats", __name__, url_prefix="/seats")


@seats_bp.get("/")
@admin_required
def index():
    """Display interactive seat layout configuration for the selected hall."""
    halls = Hall.query.order_by(Hall.is_active.desc(), Hall.hall_name.asc()).all()
    selected_hall = None
    seat_matrix = []

    if halls:
        requested_id = request.args.get("hall_id", type=int)
        if requested_id is not None:
            selected_hall = db.session.get(Hall, requested_id)
            if selected_hall is None:
                flash("Selected examination hall was not found.", "warning")
        if selected_hall is None:
            selected_hall = next((h for h in halls if h.is_active), halls[0])
        seat_matrix = get_hall_seat_matrix(selected_hall)

    return render_template(
        "seats/index.html",
        halls=halls,
        selected_hall=selected_hall,
        seat_matrix=seat_matrix,
        active_nav="seats",
    )


@seats_bp.post("/<int:seat_id>/toggle-block")
@admin_required
def toggle_block(seat_id: int):
    """Block or unblock a seat and update usable capacity immediately."""
    seat = db.get_or_404(Seat, seat_id)
    try:
        updated = toggle_seat_blocked(seat.seat_id)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        action = "blocked" if updated.is_blocked else "unblocked"
        flash(f"Seat {updated.seat_label} is now {action}.", "info")
    return redirect(url_for("seats.index", hall_id=seat.hall_id))


@seats_bp.post("/<int:seat_id>/toggle-accessible")
@admin_required
def toggle_accessible(seat_id: int):
    """Mark or unmark an unblocked seat as accessible for special-needs students."""
    seat = db.get_or_404(Seat, seat_id)
    try:
        updated = toggle_seat_accessible(seat.seat_id)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        state = "marked accessible" if updated.is_accessible else "marked standard"
        flash(f"Seat {updated.seat_label} is now {state}.", "info")
    return redirect(url_for("seats.index", hall_id=seat.hall_id))
