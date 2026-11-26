"""CSV/XLSX student import service using Pandas and OpenPyXL."""

from dataclasses import dataclass, field
from io import BytesIO
import os
from typing import BinaryIO
import zipfile

import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Student
from app.services.student_service import validate_student_inputs

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB safeguard

TEMPLATE_COLUMNS = [
    "roll_number",
    "name",
    "class_name",
    "section",
    "requires_accessible_seat",
    "accessibility_notes",
]

REQUIRED_COLUMNS = {"roll_number", "name", "class_name", "section"}

COLUMN_ALIASES = {
    "roll": "roll_number",
    "roll_no": "roll_number",
    "student_name": "name",
    "class": "class_name",
    "batch": "class_name",
    "accessible": "requires_accessible_seat",
    "special_needs": "requires_accessible_seat",
    "notes": "accessibility_notes",
}

TRUE_VALUES = {"true", "1", "yes", "y"}
FALSE_VALUES = {"", "false", "0", "no", "n"}


@dataclass
class ImportResult:
    """Outcome summary returned after validating and importing a spreadsheet."""

    created_count: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return True when zero validation errors occurred."""
        return len(self.errors) == 0


def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize header names and apply standard column aliases."""
    normalized = []
    for col in df.columns:
        clean = str(col).strip().lower().replace(" ", "_")
        normalized.append(COLUMN_ALIASES.get(clean, clean))
    df = df.copy()
    df.columns = normalized
    return df


def _parse_bool(raw_value: str, row_number: int) -> bool:
    """Parse boolean strings from spreadsheet cells with clear error reporting."""
    clean = (raw_value or "").strip().lower()
    if clean in TRUE_VALUES:
        return True
    if clean in FALSE_VALUES:
        return False
    raise ValueError(
        f"Row {row_number}: Invalid value '{raw_value}' for requires_accessible_seat "
        "(use true/false, yes/no, or 1/0)."
    )


def _validate_xlsx_container(raw_bytes: bytes) -> None:
    """Verify that raw bytes represent a valid ZIP/OOXML XLSX spreadsheet."""
    buffer = BytesIO(raw_bytes)
    if not zipfile.is_zipfile(buffer):
        raise ValueError("Invalid XLSX file: file contents do not match a valid Excel OOXML archive.")

    buffer.seek(0)
    try:
        with zipfile.ZipFile(buffer, "r") as archive:
            names = set(archive.namelist())
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise ValueError(f"Invalid or corrupted XLSX archive: {exc}") from exc

    has_content_types = "[Content_Types].xml" in names
    has_workbook = any(name.startswith("xl/") for name in names)
    if not (has_content_types and has_workbook):
        raise ValueError(
            "Invalid XLSX file: archive is missing required Excel OOXML spreadsheet structure."
        )


def _read_spreadsheet(stream: BinaryIO, filename: str) -> pd.DataFrame:
    """Read CSV or XLSX bytes into a string-typed Pandas DataFrame safely."""
    ext = os.path.splitext((filename or "").strip().lower())[1]
    if ext not in {".csv", ".xlsx"}:
        raise ValueError("Unsupported file format. Please upload a .csv or .xlsx file.")

    raw_bytes = stream.read(MAX_UPLOAD_BYTES + 1)
    if not raw_bytes:
        raise ValueError("The uploaded file is empty.")
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("The uploaded file exceeds the 5 MB size limit.")

    if ext == ".csv":
        if b"\x00" in raw_bytes:
            raise ValueError("Invalid CSV file: binary NUL bytes are not allowed.")
    else:
        _validate_xlsx_container(raw_bytes)

    buffer = BytesIO(raw_bytes)
    try:
        if ext == ".csv":
            df = pd.read_csv(buffer, dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(buffer, engine="openpyxl", dtype=str, keep_default_na=False)
    except EmptyDataError as exc:
        raise ValueError("The uploaded CSV file contains no rows or headers.") from exc
    except (ParserError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"Could not parse the uploaded file: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Invalid or corrupted spreadsheet file: {exc}") from exc

    if df.empty and len(df.columns) == 0:
        raise ValueError("The uploaded file contains no columns.")

    return _normalize_dataframe_columns(df)


def import_students_from_file(stream: BinaryIO, filename: str) -> ImportResult:
    """Validate and atomically import students from a CSV or XLSX file.

    If any row fails validation, duplicates a roll number (in the file or DB),
    or fails during database commit, zero rows are inserted and errors are returned.
    """
    try:
        df = _read_spreadsheet(stream, filename)
    except ValueError as exc:
        return ImportResult(created_count=0, errors=[str(exc)])

    if df.columns.duplicated().any():
        return ImportResult(
            created_count=0,
            errors=["Duplicate or conflicting column headers detected after normalization."],
        )

    missing_cols = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_cols:
        return ImportResult(
            created_count=0,
            errors=[f"Missing required column(s): {', '.join(missing_cols)}."],
        )

    existing_rolls = {
        row[0].strip().lower()
        for row in db.session.query(Student.roll_number).all()
        if row[0]
    }

    seen_in_file: dict[str, int] = {}
    validated_rows: list[dict] = []
    errors: list[str] = []

    for idx, row in df.iterrows():
        excel_row_num = int(idx) + 2  # Account for 1-based indexing and header row

        roll_val = str(row.get("roll_number", "")).strip()
        name_val = str(row.get("name", "")).strip()
        class_val = str(row.get("class_name", "")).strip()
        section_val = str(row.get("section", "")).strip()
        accessible_raw = str(row.get("requires_accessible_seat", "")).strip()
        notes_val = str(row.get("accessibility_notes", "")).strip()

        # Skip completely blank trailing rows
        if not any([roll_val, name_val, class_val, section_val, accessible_raw, notes_val]):
            continue

        try:
            requires_acc = _parse_bool(accessible_raw, excel_row_num)
            clean_data = validate_student_inputs(
                roll_number=roll_val,
                name=name_val,
                class_name=class_val,
                section=section_val,
                requires_accessible_seat=requires_acc,
                accessibility_notes=notes_val,
                check_db_uniqueness=False,
            )
        except ValueError as exc:
            msg = str(exc)
            errors.append(msg if msg.startswith(f"Row {excel_row_num}:") else f"Row {excel_row_num}: {msg}")
            continue

        lower_roll = clean_data["roll_number"].lower()
        if lower_roll in seen_in_file:
            first_row = seen_in_file[lower_roll]
            errors.append(
                f"Row {excel_row_num}: Duplicate roll number '{clean_data['roll_number']}' "
                f"(already listed on row {first_row})."
            )
            continue

        if lower_roll in existing_rolls:
            errors.append(
                f"Row {excel_row_num}: Roll number '{clean_data['roll_number']}' already exists in the database."
            )
            continue

        seen_in_file[lower_roll] = excel_row_num
        validated_rows.append(clean_data)

    if not validated_rows and not errors:
        errors.append("The uploaded file contains headers only and no student rows.")

    if errors:
        return ImportResult(created_count=0, errors=errors)

    students = [Student(**item) for item in validated_rows]
    try:
        db.session.add_all(students)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return ImportResult(
            created_count=0,
            errors=["Database error occurred while saving imported students. No records were saved."],
        )

    return ImportResult(created_count=len(students), errors=[])


def generate_sample_csv() -> str:
    """Return a clean header-only CSV template for student import."""
    df = pd.DataFrame(columns=TEMPLATE_COLUMNS)
    return df.to_csv(index=False)


def generate_sample_xlsx() -> bytes:
    """Return a clean header-only XLSX template generated with OpenPyXL."""
    df = pd.DataFrame(columns=TEMPLATE_COLUMNS)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Students")
    buffer.seek(0)
    return buffer.getvalue()
