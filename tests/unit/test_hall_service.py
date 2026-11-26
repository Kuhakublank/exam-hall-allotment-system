"""Phase 3 unit tests for hall_service: seat generation, capacity, and history safety."""

from datetime import date, time
import pytest

from app.models import (
    AllocationRun,
    ConstraintConfig,
    ExamSession,
    Hall,
    Seat,
    SeatingAssignment,
    Student,
)
from app.services.hall_service import (
    create_hall,
    get_eligible_seats,
    get_hall_seat_matrix,
    hall_has_historical_assignments,
    toggle_hall_active,
    toggle_seat_accessible,
    toggle_seat_blocked,
    update_hall,
)


def test_create_hall_auto_generates_unique_labeled_seats(db_session):
    """Creating a hall generates rows*columns seats with deterministic R#-C# labels."""
    hall = create_hall("Block-A-101", "Academic Block A, 1st Floor", rows=3, columns=4, capacity=12)

    assert hall.hall_name == "Block-A-101"
    assert hall.location == "Academic Block A, 1st Floor"
    assert hall.is_active is True
    assert hall.total_grid_seats == 12
    assert len(hall.seats) == 12

    labels = [s.seat_label for s in hall.seats]
    assert labels[0] == "R1-C1"
    assert labels[3] == "R1-C4"
    assert labels[-1] == "R3-C4"
    assert len({(s.row_num, s.col_num) for s in hall.seats}) == 12


def test_create_hall_validation_prevents_duplicates_and_invalid_capacity(db_session):
    """Duplicate hall names (case-insensitive) and invalid dimensions/capacity raise ValueError."""
    create_hall("Main-Hall", "Ground Floor", rows=2, columns=3, capacity=6)

    with pytest.raises(ValueError, match="already exists"):
        create_hall("main-hall", "Ground Floor", rows=2, columns=3, capacity=6)

    with pytest.raises(ValueError, match="cannot exceed total grid positions"):
        create_hall("Overflow-Hall", None, rows=2, columns=3, capacity=7)

    with pytest.raises(ValueError, match="positive"):
        create_hall("Zero-Row-Hall", None, rows=0, columns=3, capacity=1)


def test_capacity_smaller_than_grid_and_blocking_seats(db_session):
    """Verify usable_capacity = min(capacity, unblocked) and eligible seats behavior."""
    # 5x6 = 30 physical grid seats, configured capacity = 25
    hall = create_hall("Exam-Hall-30", "Block C", rows=5, columns=6, capacity=25)

    assert hall.total_grid_seats == 30
    assert hall.capacity == 25
    assert hall.unblocked_seats_count == 30
    assert hall.usable_capacity == 25
    assert len(get_eligible_seats(hall.hall_id)) == 30

    # Block 3 seats -> 27 unblocked, usable_capacity stays capped at 25
    for seat in hall.seats[:3]:
        toggle_seat_blocked(seat.seat_id)
    db_session.refresh(hall)
    assert hall.blocked_seats_count == 3
    assert hall.unblocked_seats_count == 27
    assert hall.usable_capacity == 25
    assert len(get_eligible_seats(hall.hall_id)) == 27

    # Block 4 more (7 total) -> 23 unblocked, usable_capacity drops to 23
    for seat in hall.seats[3:7]:
        toggle_seat_blocked(seat.seat_id)
    db_session.refresh(hall)
    assert hall.blocked_seats_count == 7
    assert hall.unblocked_seats_count == 23
    assert hall.usable_capacity == 23
    assert len(get_eligible_seats(hall.hall_id)) == 23

    # Unblock 3 seats -> 26 unblocked, usable_capacity returns to 25
    for seat in hall.seats[:3]:
        toggle_seat_blocked(seat.seat_id)
    db_session.refresh(hall)
    assert hall.blocked_seats_count == 4
    assert hall.usable_capacity == 25


def test_accessible_seats_and_blocked_interaction(db_session):
    """Accessible flags exclude blocked seats and cannot be enabled on blocked seats."""
    hall = create_hall("Access-Hall", "Floor 1", rows=2, columns=2, capacity=4)
    s1, s2 = hall.seats[0], hall.seats[1]

    toggle_seat_accessible(s1.seat_id)
    db_session.refresh(hall)
    assert hall.accessible_seats_count == 1

    # Blocking an accessible seat removes it from usable accessible count
    toggle_seat_blocked(s1.seat_id)
    db_session.refresh(hall)
    assert hall.accessible_seats_count == 0
    assert hall.usable_capacity == 3

    # Marking an already-blocked seat as accessible is rejected
    toggle_seat_blocked(s2.seat_id)
    with pytest.raises(ValueError, match="Unblock the seat first"):
        toggle_seat_accessible(s2.seat_id)


def test_update_hall_resizes_unused_hall_and_preserves_existing_flags(db_session):
    """Resizing an unused hall keeps flags for surviving coordinates and adds new ones."""
    hall = create_hall("Flex-Hall", "North Wing", rows=2, columns=2, capacity=4)
    toggle_seat_blocked(hall.seats[0].seat_id)  # R1-C1 blocked

    updated = update_hall(hall.hall_id, "Flex-Hall-Renamed", "East Wing", rows=2, columns=3, capacity=5)
    assert updated.hall_name == "Flex-Hall-Renamed"
    assert updated.location == "East Wing"
    assert len(updated.seats) == 6
    r1c1 = Seat.query.filter_by(hall_id=hall.hall_id, row_num=1, col_num=1).one()
    assert r1c1.is_blocked is True

    matrix = get_hall_seat_matrix(updated)
    assert len(matrix) == 2
    assert len(matrix[0]) == 3


def test_deactivation_and_resize_protection_with_historical_assignments(db_session):
    """Deactivating preserves history, and resizing a hall with assignments is blocked."""
    hall = create_hall("History-Hall", "Main Building", rows=2, columns=2, capacity=4)
    student = Student(roll_number="HIST-1", name="Student Hist", class_name="CS", section="A")
    session = ExamSession(title="Final", exam_date=date(2026, 12, 10), start_time=time(9, 0))
    db_session.add_all([student, session])
    db_session.flush()

    cfg = ConstraintConfig(session_id=session.session_id)
    db_session.add(cfg)
    db_session.flush()

    run = AllocationRun(
        session_id=session.session_id,
        config_id=cfg.config_id,
        algorithm_type="backtracking_mrv_fc",
        status="feasible",
    )
    db_session.add(run)
    db_session.flush()

    assignment = SeatingAssignment(
        run_id=run.run_id,
        session_id=session.session_id,
        student_id=student.student_id,
        hall_id=hall.hall_id,
        seat_id=hall.seats[0].seat_id,
    )
    db_session.add(assignment)
    db_session.commit()

    assert hall_has_historical_assignments(hall.hall_id) is True

    # Resizing rows/columns must be rejected
    with pytest.raises(ValueError, match="existing seating assignments"):
        update_hall(hall.hall_id, "History-Hall", "Main Building", rows=3, columns=2, capacity=4)

    # Non-structural metadata update (e.g., location/capacity) is still allowed
    update_hall(hall.hall_id, "History-Hall", "Updated Wing", rows=2, columns=2, capacity=3)
    assert hall.location == "Updated Wing"
    assert hall.capacity == 3

    # Deactivating keeps seats and historical assignment intact
    toggle_hall_active(hall.hall_id)
    assert hall.is_active is False
    assert Seat.query.filter_by(hall_id=hall.hall_id).count() == 4
    assert SeatingAssignment.query.filter_by(hall_id=hall.hall_id).count() == 1
