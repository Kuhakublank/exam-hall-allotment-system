"""Expose all SQLAlchemy models for Flask-Migrate discovery."""

from app.models.allocation import AllocationRun, ConstraintConfig, SeatingAssignment
from app.models.exam import ExamRegistration, ExamSession, Subject
from app.models.hall import Hall, Seat
from app.models.student import Student
from app.models.user import User

__all__ = [
    "User",
    "Student",
    "Hall",
    "Seat",
    "Subject",
    "ExamSession",
    "ExamRegistration",
    "ConstraintConfig",
    "AllocationRun",
    "SeatingAssignment",
]
