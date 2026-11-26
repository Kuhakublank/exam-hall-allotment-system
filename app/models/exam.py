"""Subject, ExamSession, and ExamRegistration models."""

from datetime import datetime, timezone

from app.extensions import db


class Subject(db.Model):
    """Academic subject examined during an examination session."""

    __tablename__ = "subjects"

    subject_id = db.Column(db.Integer, primary_key=True)
    subject_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    subject_name = db.Column(db.String(120), nullable=False)

    registrations = db.relationship(
        "ExamRegistration",
        back_populates="subject",
    )

    def __repr__(self) -> str:
        return f"<Subject {self.subject_code} - {self.subject_name}>"


class ExamSession(db.Model):
    """A scheduled examination time slot that can include multiple subjects."""

    __tablename__ = "exam_sessions"

    session_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    registrations = db.relationship(
        "ExamRegistration",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    constraint_configs = db.relationship(
        "ConstraintConfig",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    allocation_runs = db.relationship(
        "AllocationRun",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ExamSession {self.title} on {self.exam_date} {self.start_time}>"


class ExamRegistration(db.Model):
    """Links a student and their examined subject within a specific exam session."""

    __tablename__ = "exam_registrations"

    registration_id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.subject_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    group_label = db.Column(db.String(80), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("session_id", "student_id", name="uq_registration_session_student"),
    )

    session = db.relationship("ExamSession", back_populates="registrations")
    student = db.relationship("Student", back_populates="registrations")
    subject = db.relationship("Subject", back_populates="registrations")

    def __repr__(self) -> str:
        return (
            f"<ExamRegistration session={self.session_id} "
            f"student={self.student_id} subject={self.subject_id}>"
        )
