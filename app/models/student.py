"""Student model representing examinees and accessibility needs."""

from datetime import datetime, timezone

from app.extensions import db


class Student(db.Model):
    """Registered student eligible to participate in examination sessions."""

    __tablename__ = "students"

    student_id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    section = db.Column(db.String(30), nullable=False)
    requires_accessible_seat = db.Column(db.Boolean, nullable=False, default=False)
    accessibility_notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    registrations = db.relationship(
        "ExamRegistration",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    @property
    def default_group(self) -> str:
        """Return default configured group label (class + section, e.g., CS-A)."""
        return f"{self.class_name}-{self.section}"

    def __repr__(self) -> str:
        return f"<Student {self.roll_number} - {self.name}>"
