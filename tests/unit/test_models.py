"""Phase 1 tests for app initialization, database schema, constraints, and relationships."""

from datetime import date, time
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AllocationRun,
    ConstraintConfig,
    ExamRegistration,
    ExamSession,
    Hall,
    Seat,
    SeatingAssignment,
    Student,
    Subject,
    User,
)


def test_health_endpoint(client):
    """Flask application factory should boot and serve /health."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_all_expected_tables_created(app):
    """All core tables defined in the specification should exist in the schema."""
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    expected = {
        "users",
        "students",
        "halls",
        "seats",
        "subjects",
        "exam_sessions",
        "exam_registrations",
        "constraint_configs",
        "allocation_runs",
        "seating_assignments",
    }
    assert expected.issubset(table_names)


def test_user_password_hashing(db_session):
    """User passwords must be stored as hashes and verified properly."""
    user = User(username="exam_admin", email="admin@example.edu", role="admin")
    user.set_password("StrongPass!2026")
    db_session.add(user)
    db_session.commit()

    assert user.password_hash != "StrongPass!2026"
    assert user.check_password("StrongPass!2026") is True
    assert user.check_password("WrongPass") is False


def test_student_default_group_and_unique_roll(db_session):
    """Student default_group formats class-section, and duplicate roll numbers fail."""
    s1 = Student(
        roll_number="KU-001",
        name="Aarav Sharma",
        class_name="CS",
        section="A",
        requires_accessible_seat=True,
    )
    db_session.add(s1)
    db_session.commit()

    assert s1.default_group == "CS-A"

    s_dup = Student(
        roll_number="KU-001",
        name="Duplicate Student",
        class_name="CS",
        section="B",
    )
    db_session.add(s_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_hall_and_seat_uniqueness(db_session):
    """Each hall coordinate (row, column) can only have one seat."""
    hall = Hall(hall_name="Block-A-101", rows=2, columns=2, capacity=4)
    db_session.add(hall)
    db_session.flush()

    seat1 = Seat(hall_id=hall.hall_id, row_num=1, col_num=1, seat_label="R1-C1")
    seat_dup = Seat(hall_id=hall.hall_id, row_num=1, col_num=1, seat_label="R1-C1-DUP")
    db_session.add_all([seat1, seat_dup])

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_multi_subject_exam_session_and_unique_seat_constraints(db_session):
    """An exam session supports multiple subjects and enforces 1 student <-> 1 seat per run."""
    s1 = Student(roll_number="R-101", name="Student One", class_name="CS", section="A")
    s2 = Student(roll_number="R-102", name="Student Two", class_name="IT", section="B")
    sub1 = Subject(subject_code="COMP301", subject_name="Algorithms")
    sub2 = Subject(subject_code="MATH201", subject_name="Discrete Math")

    session = ExamSession(
        title="Midterm Slot 1",
        exam_date=date(2026, 12, 1),
        start_time=time(10, 0),
        end_time=time(12, 0),
    )
    hall = Hall(hall_name="Main-Hall", rows=1, columns=2, capacity=2)
    db_session.add_all([s1, s2, sub1, sub2, session, hall])
    db_session.flush()

    seat1 = Seat(hall_id=hall.hall_id, row_num=1, col_num=1, seat_label="R1-C1")
    seat2 = Seat(hall_id=hall.hall_id, row_num=1, col_num=2, seat_label="R1-C2")
    db_session.add_all([seat1, seat2])
    db_session.flush()

    reg1 = ExamRegistration(
        session_id=session.session_id,
        student_id=s1.student_id,
        subject_id=sub1.subject_id,
        group_label=s1.default_group,
    )
    reg2 = ExamRegistration(
        session_id=session.session_id,
        student_id=s2.student_id,
        subject_id=sub2.subject_id,
        group_label=s2.default_group,
    )
    config = ConstraintConfig(session_id=session.session_id)
    db_session.add_all([reg1, reg2, config])
    db_session.flush()

    run = AllocationRun(
        session_id=session.session_id,
        config_id=config.config_id,
        algorithm_type="backtracking_mrv_fc",
        status="feasible",
    )
    db_session.add(run)
    db_session.flush()

    a1 = SeatingAssignment(
        run_id=run.run_id,
        session_id=session.session_id,
        student_id=s1.student_id,
        hall_id=hall.hall_id,
        seat_id=seat1.seat_id,
    )
    # Attempt assigning a second student to the same seat in the same run
    a_conflict = SeatingAssignment(
        run_id=run.run_id,
        session_id=session.session_id,
        student_id=s2.student_id,
        hall_id=hall.hall_id,
        seat_id=seat1.seat_id,
    )
    db_session.add_all([a1, a_conflict])

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
