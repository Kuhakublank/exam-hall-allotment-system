"""Service layer for examination hall CRUD, seat grid generation, and capacity logic."""

from sqlalchemy import func

from app.extensions import db
from app.models import Hall, Seat, SeatingAssignment


def format_seat_label(row_num: int, col_num: int) -> str:
    """Return a consistent coordinate label such as R1-C1."""
    return f"R{row_num}-C{col_num}"


def hall_has_historical_assignments(hall_id: int) -> bool:
    """Return True if any seating assignment references this hall or any of its seats."""
    existing = (
        SeatingAssignment.query.join(Seat, SeatingAssignment.seat_id == Seat.seat_id)
        .filter((SeatingAssignment.hall_id == hall_id) | (Seat.hall_id == hall_id))
        .first()
    )
    return existing is not None


def _validate_hall_inputs(
    hall_name: str,
    location: str | None,
    rows: int,
    columns: int,
    capacity: int,
    exclude_hall_id: int | None = None,
) -> tuple[str, str | None, int, int, int]:
    """Validate and normalize hall configuration fields."""
    clean_name = (hall_name or "").strip()
    clean_location = (location or "").strip() or None

    if not clean_name:
        raise ValueError("Hall name is required.")
    if len(clean_name) > 80:
        raise ValueError("Hall name must be 80 characters or fewer.")
    if clean_location and len(clean_location) > 120:
        raise ValueError("Location must be 120 characters or fewer.")

    if not isinstance(rows, int) or rows <= 0:
        raise ValueError("Rows must be a positive whole number.")
    if not isinstance(columns, int) or columns <= 0:
        raise ValueError("Columns must be a positive whole number.")
    if not isinstance(capacity, int) or capacity <= 0:
        raise ValueError("Configured capacity must be a positive whole number.")
    if capacity > rows * columns:
        raise ValueError(
            f"Configured capacity ({capacity}) cannot exceed total grid positions ({rows * columns})."
        )

    dup_query = Hall.query.filter(func.lower(Hall.hall_name) == clean_name.lower())
    if exclude_hall_id is not None:
        dup_query = dup_query.filter(Hall.hall_id != exclude_hall_id)
    if dup_query.first() is not None:
        raise ValueError(f"An examination hall named '{clean_name}' already exists.")

    return clean_name, clean_location, rows, columns, capacity


def create_hall(
    hall_name: str,
    location: str | None,
    rows: int,
    columns: int,
    capacity: int,
) -> Hall:
    """Create a hall and automatically generate all (row, column) seat records."""
    clean_name, clean_location, rows, columns, capacity = _validate_hall_inputs(
        hall_name, location, rows, columns, capacity
    )

    hall = Hall(
        hall_name=clean_name,
        location=clean_location,
        rows=rows,
        columns=columns,
        capacity=capacity,
        is_active=True,
    )
    db.session.add(hall)
    db.session.flush()

    seats = [
        Seat(
            hall_id=hall.hall_id,
            row_num=r,
            col_num=c,
            seat_label=format_seat_label(r, c),
            is_blocked=False,
            is_accessible=False,
        )
        for r in range(1, rows + 1)
        for c in range(1, columns + 1)
    ]
    db.session.add_all(seats)
    db.session.commit()
    return hall


def update_hall(
    hall_id: int,
    hall_name: str,
    location: str | None,
    rows: int,
    columns: int,
    capacity: int,
) -> Hall:
    """Update a hall's details and safely sync its seat grid if unused in allocations."""
    hall = db.session.get(Hall, hall_id)
    if hall is None:
        raise ValueError("Examination hall not found.")

    clean_name, clean_location, rows, columns, capacity = _validate_hall_inputs(
        hall_name, location, rows, columns, capacity, exclude_hall_id=hall.hall_id
    )

    dimensions_changed = (rows != hall.rows) or (columns != hall.columns)
    if dimensions_changed:
        if hall_has_historical_assignments(hall.hall_id):
            raise ValueError(
                "Cannot resize rows or columns because this hall has existing seating assignments."
            )
        existing_by_coord = {(s.row_num, s.col_num): s for s in hall.seats}
        for coord, seat in existing_by_coord.items():
            if coord[0] > rows or coord[1] > columns:
                db.session.delete(seat)
        for r in range(1, rows + 1):
            for c in range(1, columns + 1):
                if (r, c) not in existing_by_coord:
                    db.session.add(
                        Seat(
                            hall_id=hall.hall_id,
                            row_num=r,
                            col_num=c,
                            seat_label=format_seat_label(r, c),
                            is_blocked=False,
                            is_accessible=False,
                        )
                    )

    hall.hall_name = clean_name
    hall.location = clean_location
    hall.rows = rows
    hall.columns = columns
    hall.capacity = capacity
    db.session.commit()
    return hall


def toggle_hall_active(hall_id: int) -> Hall:
    """Deactivate or reactivate a hall without deleting seats or assignment history."""
    hall = db.session.get(Hall, hall_id)
    if hall is None:
        raise ValueError("Examination hall not found.")

    hall.is_active = not hall.is_active
    db.session.commit()
    return hall


def get_eligible_seats(hall_id: int) -> list[Seat]:
    """Return all unblocked seats for a hall ordered by (row_num, col_num).

    When unblocked seats exceed hall.capacity, all unblocked seats remain
    eligible candidate positions while allocation algorithms cap total
    assigned students at hall.usable_capacity = min(hall.capacity, len(eligible)).
    """
    hall = db.session.get(Hall, hall_id)
    if hall is None:
        raise ValueError("Examination hall not found.")

    return (
        Seat.query.filter_by(hall_id=hall_id, is_blocked=False)
        .order_by(Seat.row_num.asc(), Seat.col_num.asc())
        .all()
    )


def get_hall_seat_matrix(hall: Hall) -> list[list[Seat | None]]:
    """Build a 2D (rows x columns) seat grid matrix for visual rendering."""
    by_coord = {(seat.row_num, seat.col_num): seat for seat in hall.seats}
    return [
        [by_coord.get((r, c)) for c in range(1, hall.columns + 1)]
        for r in range(1, hall.rows + 1)
    ]


def toggle_seat_blocked(seat_id: int) -> Seat:
    """Block or unblock an individual seat and persist immediately."""
    seat = db.session.get(Seat, seat_id)
    if seat is None:
        raise ValueError("Seat not found.")

    seat.is_blocked = not seat.is_blocked
    db.session.commit()
    return seat


def toggle_seat_accessible(seat_id: int) -> Seat:
    """Toggle accessibility flag on an unblocked seat."""
    seat = db.session.get(Seat, seat_id)
    if seat is None:
        raise ValueError("Seat not found.")
    if seat.is_blocked:
        raise ValueError("Blocked seats cannot be marked accessible. Unblock the seat first.")

    seat.is_accessible = not seat.is_accessible
    db.session.commit()
    return seat
