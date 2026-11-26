"""Phase 4 unit tests for Pandas/OpenPyXL CSV and XLSX student import & security."""

from io import BytesIO
import zipfile
import pandas as pd
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Student
from app.services.import_service import (
    MAX_UPLOAD_BYTES,
    generate_sample_csv,
    generate_sample_xlsx,
    import_students_from_file,
)
from app.services.student_service import create_student


def test_import_valid_csv_preserves_leading_zeros_and_booleans(db_session):
    """Valid CSV imports students accurately and keeps leading zeros in roll numbers."""
    csv_data = (
        "roll_number,name,class,section,requires_accessible_seat,accessibility_notes\n"
        "00101,Student Alpha,CS,A,yes,Wheelchair access\n"
        "00102,Student Beta,CS,B,no,\n"
        "00103,Student Gamma,IT,A,1,Ground floor\n"
    ).encode("utf-8")

    result = import_students_from_file(BytesIO(csv_data), "students.csv")
    assert result.success is True
    assert result.created_count == 3

    s1 = Student.query.filter_by(roll_number="00101").one()
    s2 = Student.query.filter_by(roll_number="00102").one()
    s3 = Student.query.filter_by(roll_number="00103").one()
    assert s1.requires_accessible_seat is True
    assert s1.accessibility_notes == "Wheelchair access"
    assert s2.requires_accessible_seat is False
    assert s3.requires_accessible_seat is True


def test_import_valid_xlsx_via_openpyxl(db_session):
    """Valid XLSX file generated with OpenPyXL imports cleanly."""
    df = pd.DataFrame(
        [
            {
                "roll_number": "EX-01",
                "name": "Excel Student One",
                "class_name": "BBA",
                "section": "A",
                "requires_accessible_seat": "false",
                "accessibility_notes": "",
            },
            {
                "roll_number": "EX-02",
                "name": "Excel Student Two",
                "class_name": "BBA",
                "section": "B",
                "requires_accessible_seat": "true",
                "accessibility_notes": "Extra space",
            },
        ]
    )
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buf.seek(0)

    result = import_students_from_file(buf, "roster.xlsx")
    assert result.success is True
    assert result.created_count == 2
    assert Student.query.count() == 2


def test_import_rejects_errors_atomically_without_partial_inserts(db_session):
    """Any row-level or duplicate error aborts the entire batch cleanly."""
    create_student("DB-DUP", "Existing Student", "CS", "A")

    bad_csv = (
        "roll_number,name,class_name,section,requires_accessible_seat\n"
        "NEW-01,Valid Row,CS,A,false\n"
        "NEW-01,Duplicate In File,CS,B,false\n"
        "DB-DUP,Duplicate In DB,CS,A,false\n"
        "NEW-02,,CS,A,maybe\n"
    ).encode("utf-8")

    result = import_students_from_file(BytesIO(bad_csv), "bad.csv")
    assert result.success is False
    assert result.created_count == 0
    assert any("Row 3:" in err and "already listed on row 2" in err for err in result.errors)
    assert any("Row 4:" in err and "already exists in the database" in err for err in result.errors)
    assert any("Row 5:" in err for err in result.errors)
    # Atomic guarantee: NEW-01 was NOT inserted
    assert Student.query.count() == 1


def test_import_rejects_missing_columns_and_unsupported_extensions(db_session):
    """Missing required columns or non-CSV/XLSX uploads return clear errors."""
    missing_col_csv = b"roll_number,name\n01,Only Two Cols\n"
    r1 = import_students_from_file(BytesIO(missing_col_csv), "missing.csv")
    assert r1.success is False
    assert "Missing required column(s): class_name, section" in r1.errors[0]

    r2 = import_students_from_file(BytesIO(b"hello"), "notes.txt")
    assert r2.success is False
    assert "Unsupported file format" in r2.errors[0]


def test_import_security_rejects_nul_bytes_fake_xlsx_corrupt_xlsx_and_oversized(db_session):
    """Reject CSV with NUL bytes, non-OOXML renamed .xlsx, corrupt .xlsx, and >5MB streams."""
    nul_csv = b"roll_number,name,class_name,section\n01,Bad\x00Name,CS,A\n"
    r_nul = import_students_from_file(BytesIO(nul_csv), "nul.csv")
    assert r_nul.success is False
    assert "binary NUL bytes" in r_nul.errors[0]

    # Plain text renamed to .xlsx
    r_fake_text = import_students_from_file(BytesIO(b"not really excel"), "fake.xlsx")
    assert r_fake_text.success is False
    assert "valid Excel OOXML archive" in r_fake_text.errors[0]

    # Regular ZIP archive (missing Excel OOXML files) renamed to .xlsx
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("hello.txt", "not a spreadsheet")
    zip_buf.seek(0)
    r_fake_zip = import_students_from_file(zip_buf, "archive.xlsx")
    assert r_fake_zip.success is False
    assert "missing required Excel OOXML" in r_fake_zip.errors[0]

    # Corrupted XLSX (valid ZIP header bytes followed by garbage)
    r_corrupt = import_students_from_file(BytesIO(b"PK\x03\x04corrupted_bytes"), "corrupt.xlsx")
    assert r_corrupt.success is False
    assert len(r_corrupt.errors) == 1

    # Oversized upload stream rejected by service safeguard
    oversized = b"a" * (MAX_UPLOAD_BYTES + 10)
    r_big = import_students_from_file(BytesIO(oversized), "huge.csv")
    assert r_big.success is False
    assert "exceeds the 5 MB size limit" in r_big.errors[0]
    assert Student.query.count() == 0


def test_import_commit_failure_rolls_back_cleanly(db_session, monkeypatch):
    """Database commit failure triggers rollback and inserts zero students."""
    rollback_called = {"count": 0}
    original_rollback = db.session.rollback

    def spy_rollback():
        rollback_called["count"] += 1
        return original_rollback()

    def fail_commit():
        raise IntegrityError("INSERT", {}, Exception("simulated db error"))

    monkeypatch.setattr(db.session, "rollback", spy_rollback)
    monkeypatch.setattr(db.session, "commit", fail_commit)

    csv_data = b"roll_number,name,class_name,section\nRB-01,Rollback Test,CS,A\n"
    result = import_students_from_file(BytesIO(csv_data), "valid.csv")

    assert result.success is False
    assert result.created_count == 0
    assert rollback_called["count"] >= 1
    assert "Database error occurred" in result.errors[0]
    assert Student.query.count() == 0


def test_sample_templates_contain_expected_headers():
    """CSV and XLSX template generators produce valid empty header-only templates."""
    csv_text = generate_sample_csv()
    assert "roll_number,name,class_name,section,requires_accessible_seat,accessibility_notes" in csv_text

    xlsx_bytes = generate_sample_xlsx()
    df = pd.read_excel(BytesIO(xlsx_bytes), engine="openpyxl")
    assert list(df.columns) == [
        "roll_number",
        "name",
        "class_name",
        "section",
        "requires_accessible_seat",
        "accessibility_notes",
    ]
    assert len(df) == 0
