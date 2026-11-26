"""Hall and Seat models representing physical examination rooms and grid layouts."""

import sqlalchemy as sa

from app.extensions import db


class Hall(db.Model):
    """Examination hall with configured grid dimensions and capacity."""

    __tablename__ = "halls"

    hall_id = db.Column(db.Integer, primary_key=True)
    hall_name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    location = db.Column(db.String(120), nullable=True)
    rows = db.Column(db.Integer, nullable=False)
    columns = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=sa.true(),
    )

    __table_args__ = (
        db.CheckConstraint("rows > 0", name="ck_hall_rows_positive"),
        db.CheckConstraint("columns > 0", name="ck_hall_columns_positive"),
        db.CheckConstraint("capacity > 0", name="ck_hall_capacity_positive"),
        db.CheckConstraint("capacity <= rows * columns", name="ck_hall_capacity_within_grid"),
    )

    seats = db.relationship(
        "Seat",
        back_populates="hall",
        cascade="all, delete-orphan",
        order_by="(Seat.row_num, Seat.col_num)",
    )

    @property
    def total_grid_seats(self) -> int:
        """Return total physical grid coordinates (rows * columns)."""
        return self.rows * self.columns

    @property
    def blocked_seats_count(self) -> int:
        """Return number of seats currently marked as blocked."""
        return sum(1 for seat in self.seats if seat.is_blocked)

    @property
    def unblocked_seats_count(self) -> int:
        """Return number of seats that are not blocked."""
        return sum(1 for seat in self.seats if not seat.is_blocked)

    @property
    def accessible_seats_count(self) -> int:
        """Return number of unblocked seats marked as accessible."""
        return sum(1 for seat in self.seats if not seat.is_blocked and seat.is_accessible)

    @property
    def usable_capacity(self) -> int:
        """Return effective seating capacity capped by both configured capacity and unblocked seats."""
        return min(self.capacity, self.unblocked_seats_count)

    def __repr__(self) -> str:
        return (
            f"<Hall {self.hall_name} ({self.rows}x{self.columns}, "
            f"cap={self.capacity}, active={self.is_active})>"
        )


class Seat(db.Model):
    """Individual seat at a (row, column) coordinate inside an examination hall."""

    __tablename__ = "seats"

    seat_id = db.Column(db.Integer, primary_key=True)
    hall_id = db.Column(
        db.Integer,
        db.ForeignKey("halls.hall_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_num = db.Column(db.Integer, nullable=False)
    col_num = db.Column(db.Integer, nullable=False)
    seat_label = db.Column(db.String(20), nullable=False)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    is_accessible = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint("hall_id", "row_num", "col_num", name="uq_seat_hall_row_col"),
        db.CheckConstraint("row_num >= 1", name="ck_seat_row_positive"),
        db.CheckConstraint("col_num >= 1", name="ck_seat_col_positive"),
    )

    hall = db.relationship("Hall", back_populates="seats")

    def __repr__(self) -> str:
        return f"<Seat {self.seat_label} (hall={self.hall_id}, blocked={self.is_blocked})>"
