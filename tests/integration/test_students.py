"""Phase 4 integration tests for Student management routes and CSV/XLSX upload."""

from datetime import date, time
from io import BytesIO
import re

import pandas as pd

from app.models import ConstraintConfig, ExamRegistration, ExamSession, Student, Subject, User


def _extract_csrf_token(html: str) -> str:
    """Extract hidden CSRF token from HTML form."""
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert match is not None, "Expected CSRF token in form HTML"
    return match.group(1)


def _login_admin(client, db_session) -> None:
    """Create and sign in a test admin user."""
    admin = User(username="student_admin", email="studadmin@test.edu", role="admin", is_active=True)
    admin.set_password("StrongPass!2026")
    db_session.add(admin)
    db_session.commit()

    page = client.get("/auth/login")
    token = _extract_csrf_token(page.get_data(as_text=True))
    resp = client.post(
        "/auth/login",
        data={"csrf_token": token, "email": "studadmin@test.edu", "password": "StrongPass!2026"},
        follow_redirects=False,
    )
    assert resp.status_code == 302


def test_student_routes_require_authentication(client):
    """Unauthenticated requests to student pages redirect to /auth/login."""
    for path in (
        "/students/",
        "/students/new",
        "/students/1/edit",
        "/students/import",
        "/students/template/csv",
        "/students/template/xlsx",
    ):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]


def test_student_crud_search_and_delete_protection_routes(client, db_session):
    """Admin can create, edit, search, and safely delete unused students."""
    _login_admin(client, db_session)

    form_page = client.get("/students/new")
    token = _extract_csrf_token(form_page.get_data(as_text=True))

    create_resp = client.post(
        "/students/new",
        data={
            "csrf_token": token,
            "roll_number": "KU-401",
            "name": "Sita Gurung",
            "class_name": "CS",
            "section": "A",
            "requires_accessible_seat": "y",
            "accessibility_notes": "Front row",
        },
        follow_redirects=True,
    )
    assert create_resp.status_code == 200
    assert "KU-401" in create_resp.get_data(as_text=True)
    assert "Sita Gurung" in create_resp.get_data(as_text=True)

    student = Student.query.filter_by(roll_number="KU-401").one()

    # Search filter works
    search_resp = client.get("/students/?q=Gurung&accessible_only=1")
    assert "KU-401" in search_resp.get_data(as_text=True)

    # Edit student
    edit_page = client.get(f"/students/{student.student_id}/edit")
    edit_resp = client.post(
        f"/students/{student.student_id}/edit",
        data={
            "csrf_token": _extract_csrf_token(edit_page.get_data(as_text=True)),
            "roll_number": "KU-401",
            "name": "Sita Gurung-Magar",
            "class_name": "CS",
            "section": "B",
            "requires_accessible_seat": "",
            "accessibility_notes": "",
        },
        follow_redirects=True,
    )
    assert "Sita Gurung-Magar" in edit_resp.get_data(as_text=True)
    assert "CS-B" in edit_resp.get_data(as_text=True)

    # Delete succeeds when student has no exam/seating records
    list_html = client.get("/students/").get_data(as_text=True)
    del_resp = client.post(
        f"/students/{student.student_id}/delete",
        data={"csrf_token": _extract_csrf_token(list_html)},
        follow_redirects=True,
    )
    assert del_resp.status_code == 200
    assert Student.query.count() == 0


def test_student_delete_blocked_with_registration_via_route(client, db_session):
    """Deleting a registered student via POST route flashes error and preserves record."""
    _login_admin(client, db_session)

    s = Student(roll_number="REG-1", name="Locked Student", class_name="IT", section="A")
    sub = Subject(subject_code="IT201", subject_name="Databases")
    sess = ExamSession(title="Exam 1", exam_date=date(2026, 12, 20), start_time=time(9, 0))
    db_session.add_all([s, sub, sess])
    db_session.flush()
    db_session.add(ConstraintConfig(session_id=sess.session_id))
    db_session.add(
        ExamRegistration(
            session_id=sess.session_id,
            student_id=s.student_id,
            subject_id=sub.subject_id,
            group_label=s.default_group,
        )
    )
    db_session.commit()

    list_html = client.get("/students/").get_data(as_text=True)
    resp = client.post(
        f"/students/{s.student_id}/delete",
        data={"csrf_token": _extract_csrf_token(list_html)},
        follow_redirects=True,
    )
    assert "Cannot delete this student" in resp.get_data(as_text=True)
    assert Student.query.count() == 1


def test_csv_and_xlsx_upload_and_template_downloads(client, db_session):
    """Admin can download templates and bulk-upload valid/invalid CSV and XLSX files."""
    _login_admin(client, db_session)

    csv_dl = client.get("/students/template/csv")
    assert csv_dl.status_code == 200
    assert b"roll_number,name,class_name,section" in csv_dl.data

    xlsx_dl = client.get("/students/template/xlsx")
    assert xlsx_dl.status_code == 200
    df_dl = pd.read_excel(BytesIO(xlsx_dl.data), engine="openpyxl")
    assert "roll_number" in df_dl.columns

    # Valid CSV upload
    import_page = client.get("/students/import")
    token = _extract_csrf_token(import_page.get_data(as_text=True))
    csv_bytes = (
        b"roll_number,name,class_name,section,requires_accessible_seat,accessibility_notes\n"
        b"IMP-01,Import One,CS,A,false,\n"
        b"IMP-02,Import Two,CS,B,true,Front seat\n"
    )
    ok_resp = client.post(
        "/students/import",
        data={
            "csrf_token": token,
            "file": (BytesIO(csv_bytes), "roster.csv"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert "Successfully imported 2 student(s)." in ok_resp.get_data(as_text=True)
    assert Student.query.count() == 2

    # Invalid XLSX upload (duplicate roll number from CSV above)
    bad_df = pd.DataFrame(
        [
            {"roll_number": "IMP-01", "name": "Dup", "class_name": "CS", "section": "A"},
            {"roll_number": "IMP-03", "name": "Valid", "class_name": "CS", "section": "B"},
        ]
    )
    xlsx_buf = BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
        bad_df.to_excel(writer, index=False)
    xlsx_buf.seek(0)

    token2 = _extract_csrf_token(client.get("/students/import").get_data(as_text=True))
    bad_resp = client.post(
        "/students/import",
        data={
            "csrf_token": token2,
            "file": (xlsx_buf, "bad.xlsx"),
        },
        content_type="multipart/form-data",
    )
    assert bad_resp.status_code == 200
    assert "already exists in the database" in bad_resp.get_data(as_text=True)
    assert Student.query.count() == 2


def test_oversized_upload_returns_http_413_and_invalid_extension_rejected(client, db_session):
    """Uploads exceeding 5 MB return HTTP 413 and unsupported extensions are rejected."""
    _login_admin(client, db_session)

    token = _extract_csrf_token(client.get("/students/import").get_data(as_text=True))
    oversized_bytes = b"x" * (5 * 1024 * 1024 + 1024)
    resp_413 = client.post(
        "/students/import",
        data={
            "csrf_token": token,
            "file": (BytesIO(oversized_bytes), "too_large.csv"),
        },
        content_type="multipart/form-data",
    )
    assert resp_413.status_code == 413
    assert "exceeds the maximum allowed size" in resp_413.get_data(as_text=True)
    assert Student.query.count() == 0

    token2 = _extract_csrf_token(client.get("/students/import").get_data(as_text=True))
    resp_bad_ext = client.post(
        "/students/import",
        data={
            "csrf_token": token2,
            "file": (BytesIO(b"hello"), "script.exe"),
        },
        content_type="multipart/form-data",
    )
    assert resp_bad_ext.status_code == 200
    assert "Unsupported file format" in resp_bad_ext.get_data(as_text=True)
    assert Student.query.count() == 0
