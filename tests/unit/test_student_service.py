"""Phase 4 unit tests for student_service CRUD, search, and deletion safety."""

from datetime import date, time
import pytest

from app.models import (
    ConstraintConfig,
    ExamRegistration,
    ExamSession,
    Student,
    Subject,
)
from app.services.student_service import (
    create_student,
    delete_student,
    get_distinct_classes,
    list_students,
    student_has_records,
    update_student,
)


def test_create_update_and_search_students(db_session):
    """CRUD operations and search/class/accessibility filters behave accurately."""
    s1 = create_student("CS-001", "Aarav Thapa", "CS", "A", True, "Front row seat")
    s2 = create_student("CS-002", "Bina Rai", "CS", "B", False, None)
    s3 = create_student("IT-001", "Chirag KC", "IT", "A", False, None)

    assert s1.default_group == "CS-A"
    assert s1.requires_accessible_seat is True
    assert get_distinct_classes() == ["CS", "IT"]

    assert len(list_students(search="aarav")) == 1
    assert len(list_students(class_filter="CS")) == 2
    assert len(list_students(accessible_only=True)) == 1

    updated = update_student(s2.student_id, "CS-002", "Bina Rai-Shrestha", "CS", "A", True, "Ground floor")
    assert updated.name == "Bina Rai-Shrestha"
    assert updated.default_group == "CS-A"
    assert updated.requires_accessible_seat is True

    # Deleting an unused student succeeds
    delete_student(s3.student_id)
    assert Student.query.count() == 2


def test_student_validation_rejects_duplicates_and_missing_fields(db_session):
    """Duplicate roll numbers (case-insensitive) and empty fields raise ValueError."""
    create_student("ROLL-10", "Student One", "CS", "A")

    with pytest.raises(ValueError, match="already exists"):
        create_student("roll-10", "Student Two", "CS", "B")

    with pytest.raises(ValueError, match="Roll number is required"):
        create_student("   ", "No Roll", "CS", "A")

    with pytest.raises(ValueError, match="Section is required"):
        create_student("ROLL-11", "No Section", "CS", "")


def test_delete_student_blocked_when_exam_registration_exists(db_session):
    """Students linked to an exam registration cannot be deleted."""
    student = create_student("LOCK-01", "Registered Student", "IT", "A")
    subject = Subject(subject_code="IT101", subject_name="Networking")
    session = ExamSession(title="Midterm", exam_date=date(2026, 12, 5), start_time=time(10, 0))
    db_session.add_all([subject, session])
    db_session.flush()
    db_session.add(ConstraintConfig(session_id=session.session_id))
    db_session.add(
        ExamRegistration(
            session_id=session.session_id,
            student_id=student.student_id,
            subject_id=subject.subject_id,
            group_label=student.default_group,
        )
    )
    db_session.commit()

    assert student_has_records(student.student_id) is True
    with pytest.raises(ValueError, match="existing exam registrations"):
        delete_student(student.student_id)
    assert Student.query.count() == 1
