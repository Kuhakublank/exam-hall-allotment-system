"""Phase 2 integration tests for authentication, route protection, CSRF, and dashboard."""

from datetime import date, time, timedelta
import re
import pytest

from app.models import (
    AllocationRun,
    ConstraintConfig,
    ExamSession,
    Hall,
    Student,
    Subject,
    User,
)


PROTECTED_ROUTES = [
    "/",
    "/dashboard",
    "/students/",
    "/subjects/",
    "/exams/",
    "/halls/",
    "/seats/",
    "/constraints/",
    "/allocations/halls",
    "/allocations/seating",
    "/allocations/validation",
    "/reports/",
    "/settings",
]


def _extract_csrf_token(html: str) -> str:
    """Extract the hidden CSRF token from a rendered HTML form."""
    match = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"',
        html,
    )
    assert match is not None, "Expected CSRF token in form HTML"
    return match.group(1)


def _create_user(db_session, username: str, email: str, password: str, role: str = "admin"):
    """Helper to insert a test user directly into the isolated test database."""
    user = User(username=username, email=email, role=role, is_active=True)
    user.set_password(password)
    db_session.add(user)
    db_session.commit()
    return user


def _login_client(client, email: str, password: str):
    """Fetch /auth/login for CSRF token and submit credentials."""
    login_page = client.get("/auth/login")
    token = _extract_csrf_token(login_page.get_data(as_text=True))
    return client.post(
        "/auth/login",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=False,
    )


@pytest.mark.parametrize("route_path", PROTECTED_ROUTES)
def test_unauthenticated_access_blocked_on_all_protected_routes(client, route_path):
    """Unauthenticated direct URL requests must redirect to /auth/login."""
    response = client.get(route_path, follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_login_requires_csrf_token(client, db_session):
    """POST /auth/login without a CSRF token must be rejected with 400."""
    _create_user(db_session, "admin", "admin@test.edu", "ValidPass!123")
    response = client.post(
        "/auth/login",
        data={"email": "admin@test.edu", "password": "ValidPass!123"},
    )
    assert response.status_code == 400


def test_successful_admin_login_and_protected_route_access(client, db_session):
    """Valid admin credentials log in and grant access to dashboard and module routes."""
    _create_user(db_session, "admin", "admin@test.edu", "ValidPass!123")

    resp = _login_client(client, "admin@test.edu", "ValidPass!123")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/dashboard")

    for route_path in PROTECTED_ROUTES:
        page = client.get(route_path)
        assert page.status_code == 200, f"Expected 200 for {route_path}"


def test_incorrect_password_and_unknown_email_return_uniform_error(client, db_session):
    """Failed logins must not reveal whether the email address exists."""
    _create_user(db_session, "admin", "admin@test.edu", "ValidPass!123")

    wrong_pw = _login_client(client, "admin@test.edu", "WrongPassword!")
    assert wrong_pw.status_code == 401
    wrong_pw_body = wrong_pw.get_data(as_text=True)

    unknown_email = _login_client(client, "nobody@test.edu", "WrongPassword!")
    assert unknown_email.status_code == 401
    unknown_email_body = unknown_email.get_data(as_text=True)

    assert "Invalid email or password." in wrong_pw_body
    assert "Invalid email or password." in unknown_email_body


def test_non_admin_user_forbidden(client, db_session):
    """Non-admin accounts are rejected at login and blocked with 403 on admin routes."""
    viewer = _create_user(db_session, "viewer", "viewer@test.edu", "ValidPass!123", role="viewer")
    resp = _login_client(client, "viewer@test.edu", "ValidPass!123")
    assert resp.status_code == 401

    # Tampering only _user_id in session cookie is blocked by session_protection='strong'
    with client.session_transaction() as sess:
        sess["_user_id"] = str(viewer.user_id)
    tampered_resp = client.get("/dashboard", follow_redirects=False)
    assert tampered_resp.status_code == 302
    assert "/auth/login" in tampered_resp.headers["Location"]

    # An authenticated session whose role is not 'admin' receives 403 from @admin_required
    admin = _create_user(db_session, "demoted", "demoted@test.edu", "ValidPass!123", role="admin")
    login_resp = _login_client(client, "demoted@test.edu", "ValidPass!123")
    assert login_resp.status_code == 302

    admin.role = "viewer"
    db_session.commit()

    dashboard_resp = client.get("/dashboard")
    assert dashboard_resp.status_code == 403


def test_logout_invalidates_session(client, db_session):
    """Logging out must clear the session and block subsequent protected access."""
    _create_user(db_session, "admin", "admin@test.edu", "ValidPass!123")
    login_resp = _login_client(client, "admin@test.edu", "ValidPass!123")
    assert login_resp.status_code == 302

    dashboard_resp = client.get("/dashboard")
    assert dashboard_resp.status_code == 200
    csrf_token = _extract_csrf_token(dashboard_resp.get_data(as_text=True))

    logout_resp = client.post(
        "/auth/logout",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert logout_resp.status_code == 302
    assert "/auth/login" in logout_resp.headers["Location"]

    # After logout, protected routes must redirect back to login
    after_logout = client.get("/dashboard", follow_redirects=False)
    assert after_logout.status_code == 302
    assert "/auth/login" in after_logout.headers["Location"]


def test_dashboard_empty_database_state(client, db_session):
    """Dashboard renders zero counts and empty states when no domain records exist."""
    _create_user(db_session, "admin", "admin@test.edu", "ValidPass!123")
    _login_client(client, "admin@test.edu", "ValidPass!123")

    response = client.get("/dashboard")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Administration Dashboard" in html
    assert "No upcoming examination sessions found in the database." in html
    assert "No seating allocation runs have been executed yet." in html


def test_dashboard_displays_live_database_statistics(client, db_session):
    """Dashboard counts and tables must reflect actual database rows."""
    _create_user(db_session, "admin", "admin@test.edu", "ValidPass!123")

    s1 = Student(roll_number="SYN-01", name="Student A", class_name="CS", section="A")
    s2 = Student(roll_number="SYN-02", name="Student B", class_name="CS", section="B")
    h1 = Hall(hall_name="Hall-101", rows=4, columns=5, capacity=20)
    sub1 = Subject(subject_code="CS101", subject_name="Intro CS")
    sub2 = Subject(subject_code="MA101", subject_name="Calculus")
    sub3 = Subject(subject_code="PH101", subject_name="Physics")

    tomorrow = date.today() + timedelta(days=1)
    exam = ExamSession(
        title="Midterm Slot Alpha",
        exam_date=tomorrow,
        start_time=time(9, 30),
    )
    db_session.add_all([s1, s2, h1, sub1, sub2, sub3, exam])
    db_session.flush()

    cfg = ConstraintConfig(session_id=exam.session_id)
    db_session.add(cfg)
    db_session.flush()

    run = AllocationRun(
        session_id=exam.session_id,
        config_id=cfg.config_id,
        algorithm_type="backtracking_mrv_fc",
        status="feasible",
        processing_time_ms=42,
    )
    db_session.add(run)
    db_session.commit()

    _login_client(client, "admin@test.edu", "ValidPass!123")
    response = client.get("/dashboard")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Midterm Slot Alpha" in html
    assert "backtracking_mrv_fc" in html
    assert "feasible" in html
    # Verify exact DB counts appear in summary cards
    assert ">2<" in html  # 2 students
    assert ">1<" in html  # 1 hall / 1 session
    assert ">3<" in html  # 3 subjects
