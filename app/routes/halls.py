"""Examination hall management routes blueprint."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.extensions import db
from app.models import Hall
from app.services.auth_service import admin_required
from app.services.hall_service import (
    create_hall,
    get_hall_seat_matrix,
    hall_has_historical_assignments,
    toggle_hall_active,
    update_hall,
)

halls_bp = Blueprint("halls", __name__, url_prefix="/halls")


class HallForm(FlaskForm):
    """CSRF-protected form for creating and editing examination halls."""

    hall_name = StringField(
        "Hall Name",
        validators=[
            DataRequired(message="Hall name is required."),
            Length(max=80, message="Hall name must be 80 characters or fewer."),
        ],
    )
    location = StringField(
        "Location / Building",
        validators=[
            Optional(),
            Length(max=120, message="Location must be 120 characters or fewer."),
        ],
    )
    rows = IntegerField(
        "Rows",
        validators=[
            DataRequired(message="Number of rows is required."),
            NumberRange(min=1, message="Rows must be at least 1."),
        ],
    )
    columns = IntegerField(
        "Columns",
        validators=[
            DataRequired(message="Number of columns is required."),
            NumberRange(min=1, message="Columns must be at least 1."),
        ],
    )
    capacity = IntegerField(
        "Configured Capacity",
        validators=[
            DataRequired(message="Configured capacity is required."),
            NumberRange(min=1, message="Capacity must be at least 1."),
        ],
    )


@halls_bp.get("/")
@admin_required
def index():
    """List all active and inactive examination halls."""
    halls = Hall.query.order_by(Hall.is_active.desc(), Hall.hall_name.asc()).all()
    return render_template("halls/index.html", halls=halls, active_nav="halls")


@halls_bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    """Create a new examination hall and auto-generate its seat layout."""
    form = HallForm()
    if form.validate_on_submit():
        try:
            hall = create_hall(
                hall_name=form.hall_name.data,
                location=form.location.data,
                rows=form.rows.data,
                columns=form.columns.data,
                capacity=form.capacity.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash(
                f"Hall '{hall.hall_name}' created with {hall.total_grid_seats} seats.",
                "success",
            )
            return redirect(url_for("halls.detail", hall_id=hall.hall_id))

    return render_template(
        "halls/form.html",
        form=form,
        hall=None,
        has_history=False,
        active_nav="halls",
    )


@halls_bp.get("/<int:hall_id>")
@admin_required
def detail(hall_id: int):
    """Display hall configuration details, capacity breakdown, and visual seat map."""
    hall = db.get_or_404(Hall, hall_id)
    seat_matrix = get_hall_seat_matrix(hall)
    has_history = hall_has_historical_assignments(hall.hall_id)
    return render_template(
        "halls/detail.html",
        hall=hall,
        seat_matrix=seat_matrix,
        has_history=has_history,
        active_nav="halls",
    )


@halls_bp.route("/<int:hall_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(hall_id: int):
    """Edit an examination hall while protecting historical seat assignments."""
    hall = db.get_or_404(Hall, hall_id)
    has_history = hall_has_historical_assignments(hall.hall_id)
    form = HallForm(obj=hall)

    if form.validate_on_submit():
        try:
            update_hall(
                hall_id=hall.hall_id,
                hall_name=form.hall_name.data,
                location=form.location.data,
                rows=form.rows.data,
                columns=form.columns.data,
                capacity=form.capacity.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Hall '{hall.hall_name}' updated successfully.", "success")
            return redirect(url_for("halls.detail", hall_id=hall.hall_id))

    return render_template(
        "halls/form.html",
        form=form,
        hall=hall,
        has_history=has_history,
        active_nav="halls",
    )


@halls_bp.post("/<int:hall_id>/toggle-active")
@admin_required
def toggle_active(hall_id: int):
    """Deactivate or reactivate a hall without deleting seats or history."""
    db.get_or_404(Hall, hall_id)
    try:
        hall = toggle_hall_active(hall_id)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        state_text = "reactivated" if hall.is_active else "deactivated"
        flash(f"Hall '{hall.hall_name}' has been {state_text}.", "info")
    return redirect(url_for("halls.index"))
