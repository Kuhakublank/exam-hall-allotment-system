"""Constraint configuration, allocation run history, and seating assignment models."""

from datetime import datetime, timezone

from app.extensions import db


class ConstraintConfig(db.Model):
    """Configurable separation, accessibility, and solver settings for an exam session."""

    __tablename__ = "constraint_configs"

    config_id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    separate_same_subject = db.Column(db.Boolean, nullable=False, default=True)
    separate_same_group = db.Column(db.Boolean, nullable=False, default=True)
    group_rule = db.Column(db.String(30), nullable=False, default="class_section")
    accessibility_mandatory = db.Column(db.Boolean, nullable=False, default=True)
    deterministic = db.Column(db.Boolean, nullable=False, default=True)
    random_seed = db.Column(db.Integer, nullable=True)
    max_nodes = db.Column(db.Integer, nullable=False, default=100000)
    time_limit_seconds = db.Column(db.Integer, nullable=False, default=10)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint("max_nodes > 0", name="ck_config_max_nodes_positive"),
        db.CheckConstraint("time_limit_seconds > 0", name="ck_config_time_limit_positive"),
    )

    session = db.relationship("ExamSession", back_populates="constraint_configs")
    allocation_runs = db.relationship("AllocationRun", back_populates="config")

    def __repr__(self) -> str:
        return f"<ConstraintConfig {self.config_id} session={self.session_id}>"


class AllocationRun(db.Model):
    """Metadata and evaluation metrics for one execution of a seating algorithm."""

    __tablename__ = "allocation_runs"

    run_id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    config_id = db.Column(
        db.Integer,
        db.ForeignKey("constraint_configs.config_id", ondelete="RESTRICT"),
        nullable=False,
    )
    algorithm_type = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    is_authorized = db.Column(db.Boolean, nullable=False, default=False)
    processing_time_ms = db.Column(db.Integer, nullable=False, default=0)
    placements_tried = db.Column(db.Integer, nullable=False, default=0)
    backtracks_count = db.Column(db.Integer, nullable=False, default=0)
    status_message = db.Column(db.String(500), nullable=True)
    metrics_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    session = db.relationship("ExamSession", back_populates="allocation_runs")
    config = db.relationship("ConstraintConfig", back_populates="allocation_runs")
    assignments = db.relationship(
        "SeatingAssignment",
        back_populates="run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AllocationRun {self.run_id} {self.algorithm_type} ({self.status})>"


class SeatingAssignment(db.Model):
    """Assigns one student to one seat in one hall for a specific allocation run."""

    __tablename__ = "seating_assignments"

    assignment_id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.Integer,
        db.ForeignKey("allocation_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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
    )
    hall_id = db.Column(
        db.Integer,
        db.ForeignKey("halls.hall_id", ondelete="CASCADE"),
        nullable=False,
    )
    seat_id = db.Column(
        db.Integer,
        db.ForeignKey("seats.seat_id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint("run_id", "student_id", name="uq_assignment_run_student"),
        db.UniqueConstraint("run_id", "seat_id", name="uq_assignment_run_seat"),
    )

    run = db.relationship("AllocationRun", back_populates="assignments")
    student = db.relationship("Student")
    hall = db.relationship("Hall")
    seat = db.relationship("Seat")

    def __repr__(self) -> str:
        return (
            f"<SeatingAssignment run={self.run_id} "
            f"student={self.student_id} seat={self.seat_id}>"
        )
