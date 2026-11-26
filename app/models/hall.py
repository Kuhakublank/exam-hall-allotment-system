"""Hall and Seat models representing physical examination rooms and grid layouts."""

from app.extensions import db


class Hall(db.Model):
    """Examination hall with configured grid dimensions and capacity."""

    __tablename__ = "halls"

    hall_id = db.Column(db.Integer, primary_key=True)
    hall_name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    rows = db.Column(db.Integer, nullable=False)
    columns = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

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

    def __repr__(self) -> str:
        return f"<Hall {self.hall_name} ({self.rows}x{self.columns}, cap={self.capacity})>"


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
