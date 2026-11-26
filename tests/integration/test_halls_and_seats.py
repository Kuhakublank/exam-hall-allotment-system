"""Phase 3 integration tests for Hall & Seat management routes, validation, and UI."""

from datetime import date, time
import re

from app.models import (
    AllocationRun,
    ConstraintConfig,
    ExamSession,
    Hall,
    Seat,
    SeatingAssignment,
    Student,
    User,
)


def _extract_csrf_token(html: str) -> str:
    """Extract CSRF token from rendered form HTML."""
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert match is not None, "Expected CSRF token in form HTML"
    return match.group(1)


def _login_admin(client, db_session) -> None:
    """Create and sign in a test admin user."""
    admin = User(username="hall_admin", email="halladmin@test.edu", role="admin", is_active=True)
    admin.set_password("StrongPass!2026")
    db_session.add(admin)
    db_session.commit()

    page = client.get("/auth/login")
    token = _extract_csrf_token(page.get_data(as_text=True))
    resp = client.post(
        "/auth/login",
        data={"csrf_token": token, "email": "halladmin@test.edu", "password": "StrongPass!2026"},
        follow_redirects=False,
    )
    assert resp.status_code == 302


def test_hall_and_seat_routes_require_authentication(client):
    """Direct URL access to hall and seat pages/actions redirects unauthenticated users."""
    for path in ("/halls/", "/halls/new", "/halls/1", "/halls/1/edit", "/seats/"):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]


def test_create_view_and_validate_hall_flow(client, db_session):
    """Admin can create a 5x6 hall with capacity=25, view its layout, and see validation errors."""
    _login_admin(client, db_session)

    form_page = client.get("/halls/new")
    assert form_page.status_code == 200
    token = _extract_csrf_token(form_page.get_data(as_text=True))

    create_resp = client.post(
        "/halls/new",
        data={
            "csrf_token": token,
            "hall_name": "Science-Block-201",
            "location": "Science Block, 2nd Floor",
            "rows": 5,
            "columns": 6,
            "capacity": 25,
        },
        follow_redirects=True,
    )
    html = create_resp.get_data(as_text=True)
    assert create_resp.status_code == 200
    assert "Science-Block-201" in html
    assert "R1-C1" in html
    assert "R5-C6" in html
    assert "30</strong> unblocked seats remain selectable" in html

    hall = Hall.query.filter_by(hall_name="Science-Block-201").one()
    assert len(hall.seats) == 30
    assert hall.usable_capacity == 25

    # Reject invalid capacity > rows * columns
    bad_resp = client.post(
        "/halls/new",
        data={
            "csrf_token": _extract_csrf_token(client.get("/halls/new").get_data(as_text=True)),
            "hall_name": "Bad-Hall",
            "location": "Basement",
            "rows": 2,
            "columns": 2,
            "capacity": 5,
        },
    )
    assert bad_resp.status_code == 200
    assert "cannot exceed total grid positions" in bad_resp.get_data(as_text=True)
    assert Hall.query.filter_by(hall_name="Bad-Hall").first() is None


def test_seat_block_unblock_and_accessible_updates_usable_capacity(client, db_session):
    """Blocking/unblocking seats via UI routes updates usable capacity and visual classes."""
    _login_admin(client, db_session)

    form_page = client.get("/halls/new")
    client.post(
        "/halls/new",
        data={
            "csrf_token": _extract_csrf_token(form_page.get_data(as_text=True)),
            "hall_name": "Capacity-Hall",
            "location": "Block B",
            "rows": 2,
            "columns": 3,
            "capacity": 5,
        },
    )
    hall = Hall.query.filter_by(hall_name="Capacity-Hall").one()
    seats = Seat.query.filter_by(hall_id=hall.hall_id).order_by(Seat.seat_id).all()

    seats_page = client.get(f"/seats/?hall_id={hall.hall_id}")
    assert seats_page.status_code == 200
    token = _extract_csrf_token(seats_page.get_data(as_text=True))

    # Mark first seat accessible
    acc_resp = client.post(
        f"/seats/{seats[0].seat_id}/toggle-accessible",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert acc_resp.status_code == 200
    assert "seat-accessible" in acc_resp.get_data(as_text=True)

    # Block 1 seat -> 5 unblocked, usable_capacity stays 5
    client.post(f"/seats/{seats[1].seat_id}/toggle-block", data={"csrf_token": token})
    db_session.refresh(hall)
    assert hall.usable_capacity == 5

    # Block 2nd seat -> 4 unblocked, usable_capacity drops to 4
    block_resp = client.post(
        f"/seats/{seats[2].seat_id}/toggle-block",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    html = block_resp.get_data(as_text=True)
    assert "seat-blocked" in html
    db_session.refresh(hall)
    assert hall.blocked_seats_count == 2
    assert hall.usable_capacity == 4

    # Unblock 2nd seat -> usable_capacity returns to 5
    client.post(f"/seats/{seats[2].seat_id}/toggle-block", data={"csrf_token": token})
    db_session.refresh(hall)
    assert hall.usable_capacity == 5


def test_hall_deactivation_and_edit_history_protection_routes(client, db_session):
    """Deactivating preserves assignments and editing prevents resizing used halls."""
    _login_admin(client, db_session)

    client.post(
        "/halls/new",
        data={
            "csrf_token": _extract_csrf_token(client.get("/halls/new").get_data(as_text=True)),
            "hall_name": "Protected-Hall",
            "location": "Block D",
            "rows": 2,
            "columns": 2,
            "capacity": 4,
        },
    )
    hall = Hall.query.filter_by(hall_name="Protected-Hall").one()

    # Create a historical assignment referencing this hall
    student = Student(roll_number="P3-01", name="Student P3", class_name="IT", section="A")
    session = ExamSession(title="Slot P3", exam_date=date(2026, 12, 15), start_time=time(10, 0))
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
    db_session.add(
        SeatingAssignment(
            run_id=run.run_id,
            session_id=session.session_id,
            student_id=student.student_id,
            hall_id=hall.hall_id,
            seat_id=hall.seats[0].seat_id,
        )
    )
    db_session.commit()

    # Attempting to resize via /halls/<id>/edit is blocked with an error flash
    edit_page = client.get(f"/halls/{hall.hall_id}/edit")
    assert "Rows and columns are locked" in edit_page.get_data(as_text=True)

    resize_resp = client.post(
        f"/halls/{hall.hall_id}/edit",
        data={
            "csrf_token": _extract_csrf_token(edit_page.get_data(as_text=True)),
            "hall_name": "Protected-Hall",
            "location": "Block D",
            "rows": 3,
            "columns": 2,
            "capacity": 4,
        },
    )
    assert "Cannot resize rows or columns" in resize_resp.get_data(as_text=True)
    db_session.refresh(hall)
    assert hall.rows == 2

    # Deactivating keeps hall, seats, and assignment intact
    list_page = client.get("/halls/")
    deact_resp = client.post(
        f"/halls/{hall.hall_id}/toggle-active",
        data={"csrf_token": _extract_csrf_token(list_page.get_data(as_text=True))},
        follow_redirects=True,
    )
    assert "Inactive" in deact_resp.get_data(as_text=True)
    db_session.refresh(hall)
    assert hall.is_active is False
    assert Seat.query.filter_by(hall_id=hall.hall_id).count() == 4
    assert SeatingAssignment.query.filter_by(hall_id=hall.hall_id).count() == 1
