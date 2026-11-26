"""Service layer for student CRUD, validation, search, and historical protection."""

from sqlalchemy import func, or_

from app.extensions import db
from app.models import ExamRegistration, SeatingAssignment, Student


def validate_student_inputs(
    roll_number: str,
    name: str,
    class_name: str,
    section: str,
    requires_accessible_seat: bool = False,
    accessibility_notes: str | None = None,
    exclude_student_id: int | None = None,
    check_db_uniqueness: bool = True,
) -> dict:
    """Validate and normalize student fields, raising ValueError on invalid data."""
    clean_roll = (roll_number or "").strip()
    clean_name = (name or "").strip()
    clean_class = (class_name or "").strip()
    clean_section = (section or "").strip()
    clean_notes = (accessibility_notes or "").strip() or None

    if not clean_roll:
        raise ValueError("Roll number is required.")
    if len(clean_roll) > 50:
        raise ValueError("Roll number must be 50 characters or fewer.")
    if not clean_name:
        raise ValueError("Student name is required.")
    if len(clean_name) > 120:
        raise ValueError("Student name must be 120 characters or fewer.")
    if not clean_class:
        raise ValueError("Class/Batch is required.")
    if len(clean_class) > 50:
        raise ValueError("Class/Batch must be 50 characters or fewer.")
    if not clean_section:
        raise ValueError("Section is required.")
    if len(clean_section) > 30:
        raise ValueError("Section must be 30 characters or fewer.")
    if clean_notes and len(clean_notes) > 255:
        raise ValueError("Accessibility notes must be 255 characters or fewer.")

    if check_db_uniqueness:
        dup_query = Student.query.filter(
            func.lower(Student.roll_number) == clean_roll.lower()
        )
        if exclude_student_id is not None:
            dup_query = dup_query.filter(Student.student_id != exclude_student_id)
        if dup_query.first() is not None:
            raise ValueError(f"A student with roll number '{clean_roll}' already exists.")

    return {
        "roll_number": clean_roll,
        "name": clean_name,
        "class_name": clean_class,
        "section": clean_section,
        "requires_accessible_seat": bool(requires_accessible_seat),
        "accessibility_notes": clean_notes,
    }


def list_students(
    search: str | None = None,
    class_filter: str | None = None,
    accessible_only: bool = False,
) -> list[Student]:
    """Return students filtered by search term, class, or accessibility flag."""
    query = Student.query

    clean_search = (search or "").strip()
    if clean_search:
        pattern = f"%{clean_search}%"
        query = query.filter(
            or_(
                Student.roll_number.ilike(pattern),
                Student.name.ilike(pattern),
                Student.class_name.ilike(pattern),
                Student.section.ilike(pattern),
            )
        )

    clean_class = (class_filter or "").strip()
    if clean_class:
        query = query.filter(Student.class_name == clean_class)

    if accessible_only:
        query = query.filter(Student.requires_accessible_seat.is_(True))

    return query.order_by(Student.class_name.asc(), Student.section.asc(), Student.roll_number.asc()).all()


def get_distinct_classes() -> list[str]:
    """Return sorted distinct class names present in the students table."""
    rows = db.session.query(Student.class_name).distinct().order_by(Student.class_name.asc()).all()
    return [row[0] for row in rows if row[0]]


def create_student(
    roll_number: str,
    name: str,
    class_name: str,
    section: str,
    requires_accessible_seat: bool = False,
    accessibility_notes: str | None = None,
) -> Student:
    """Validate and persist a new student record."""
    data = validate_student_inputs(
        roll_number=roll_number,
        name=name,
        class_name=class_name,
        section=section,
        requires_accessible_seat=requires_accessible_seat,
        accessibility_notes=accessibility_notes,
    )
    student = Student(**data)
    db.session.add(student)
    db.session.commit()
    return student


def update_student(
    student_id: int,
    roll_number: str,
    name: str,
    class_name: str,
    section: str,
    requires_accessible_seat: bool = False,
    accessibility_notes: str | None = None,
) -> Student:
    """Validate and update an existing student record."""
    student = db.session.get(Student, student_id)
    if student is None:
        raise ValueError("Student not found.")

    data = validate_student_inputs(
        roll_number=roll_number,
        name=name,
        class_name=class_name,
        section=section,
        requires_accessible_seat=requires_accessible_seat,
        accessibility_notes=accessibility_notes,
        exclude_student_id=student.student_id,
    )

    for key, value in data.items():
        setattr(student, key, value)
    db.session.commit()
    return student


def student_has_records(student_id: int) -> bool:
    """Return True if the student is linked to any exam registrations or seating assignments."""
    has_reg = ExamRegistration.query.filter_by(student_id=student_id).first() is not None
    if has_reg:
        return True
    return SeatingAssignment.query.filter_by(student_id=student_id).first() is not None


def delete_student(student_id: int) -> None:
    """Delete a student only when no historical exam registrations or seating records exist."""
    student = db.session.get(Student, student_id)
    if student is None:
        raise ValueError("Student not found.")
    if student_has_records(student.student_id):
        raise ValueError(
            "Cannot delete this student because they have existing exam registrations or seating records."
        )
    db.session.delete(student)
    db.session.commit()
