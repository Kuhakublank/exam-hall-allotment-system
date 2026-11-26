"""Student management and CSV/XLSX import routes blueprint."""

from io import BytesIO
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, StringField
from wtforms.validators import DataRequired, Length, Optional

from app.extensions import db
from app.models import Student
from app.services.auth_service import admin_required
from app.services.import_service import (
    generate_sample_csv,
    generate_sample_xlsx,
    import_students_from_file,
)
from app.services.student_service import (
    create_student,
    delete_student,
    get_distinct_classes,
    list_students,
    student_has_records,
    update_student,
)

students_bp = Blueprint("students", __name__, url_prefix="/students")


class StudentForm(FlaskForm):
    """CSRF-protected form for creating and editing student records."""

    roll_number = StringField(
        "Roll Number",
        validators=[
            DataRequired(message="Roll number is required."),
            Length(max=50, message="Roll number must be 50 characters or fewer."),
        ],
    )
    name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Student name is required."),
            Length(max=120, message="Student name must be 120 characters or fewer."),
        ],
    )
    class_name = StringField(
        "Class / Batch",
        validators=[
            DataRequired(message="Class/Batch is required."),
            Length(max=50, message="Class/Batch must be 50 characters or fewer."),
        ],
    )
    section = StringField(
        "Section",
        validators=[
            DataRequired(message="Section is required."),
            Length(max=30, message="Section must be 30 characters or fewer."),
        ],
    )
    requires_accessible_seat = BooleanField("Requires Accessible Seat")
    accessibility_notes = StringField(
        "Accessibility Notes (Optional)",
        validators=[
            Optional(),
            Length(max=255, message="Notes must be 255 characters or fewer."),
        ],
    )


class StudentImportForm(FlaskForm):
    """CSRF-protected form for CSV/XLSX bulk student import."""

    file = FileField(
        "Student Roster File (.csv or .xlsx)",
        validators=[
            FileRequired(message="Please choose a .csv or .xlsx file."),
            FileAllowed(["csv", "xlsx"], message="Unsupported file format. Please upload a .csv or .xlsx file."),
        ],
    )


@students_bp.get("/")
@admin_required
def index():
    """List, search, and filter registered students."""
    search = request.args.get("q", "").strip()
    class_filter = request.args.get("class_name", "").strip()
    accessible_only = request.args.get("accessible_only") == "1"

    students = list_students(
        search=search or None,
        class_filter=class_filter or None,
        accessible_only=accessible_only,
    )
    classes = get_distinct_classes()
    total_count = Student.query.count()
    accessible_count = Student.query.filter_by(requires_accessible_seat=True).count()

    return render_template(
        "students/index.html",
        students=students,
        classes=classes,
        search=search,
        class_filter=class_filter,
        accessible_only=accessible_only,
        total_count=total_count,
        accessible_count=accessible_count,
        active_nav="students",
    )


@students_bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    """Add a single student record."""
    form = StudentForm()
    if form.validate_on_submit():
        try:
            student = create_student(
                roll_number=form.roll_number.data,
                name=form.name.data,
                class_name=form.class_name.data,
                section=form.section.data,
                requires_accessible_seat=form.requires_accessible_seat.data,
                accessibility_notes=form.accessibility_notes.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Student '{student.name}' ({student.roll_number}) added.", "success")
            return redirect(url_for("students.index"))

    return render_template(
        "students/form.html",
        form=form,
        student=None,
        active_nav="students",
    )


@students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(student_id: int):
    """Edit an existing student record."""
    student = db.get_or_404(Student, student_id)
    form = StudentForm(obj=student)

    if form.validate_on_submit():
        try:
            updated = update_student(
                student_id=student.student_id,
                roll_number=form.roll_number.data,
                name=form.name.data,
                class_name=form.class_name.data,
                section=form.section.data,
                requires_accessible_seat=form.requires_accessible_seat.data,
                accessibility_notes=form.accessibility_notes.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Student '{updated.name}' updated.", "success")
            return redirect(url_for("students.index"))

    return render_template(
        "students/form.html",
        form=form,
        student=student,
        active_nav="students",
    )


@students_bp.post("/<int:student_id>/delete")
@admin_required
def delete(student_id: int):
    """Delete a student if they have no exam or seating history."""
    student = db.get_or_404(Student, student_id)
    if student_has_records(student.student_id):
        flash(
            "Cannot delete this student because they have existing exam registrations or seating records.",
            "danger",
        )
        return redirect(url_for("students.index"))

    try:
        delete_student(student.student_id)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"Student '{student.name}' ({student.roll_number}) removed.", "info")
    return redirect(url_for("students.index"))


@students_bp.route("/import", methods=["GET", "POST"])
@admin_required
def import_students():
    """Bulk-import students from a CSV or XLSX spreadsheet."""
    form = StudentImportForm()
    import_errors: list[str] = []

    if form.validate_on_submit():
        uploaded = form.file.data
        result = import_students_from_file(uploaded.stream, uploaded.filename)
        if result.success:
            flash(f"Successfully imported {result.created_count} student(s).", "success")
            return redirect(url_for("students.index"))
        import_errors = result.errors
        flash("Import failed. Please fix the reported row/column issues and try again.", "danger")

    return render_template(
        "students/import.html",
        form=form,
        import_errors=import_errors,
        active_nav="students",
    )


@students_bp.get("/template/<string:fmt>")
@admin_required
def download_template(fmt: str):
    """Download a clean CSV or XLSX template for bulk student import."""
    fmt_clean = fmt.strip().lower()
    if fmt_clean == "csv":
        csv_bytes = generate_sample_csv().encode("utf-8")
        return send_file(
            BytesIO(csv_bytes),
            mimetype="text/csv",
            as_attachment=True,
            download_name="students_template.csv",
        )
    if fmt_clean == "xlsx":
        xlsx_bytes = generate_sample_xlsx()
        return send_file(
            BytesIO(xlsx_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="students_template.xlsx",
        )
    abort(404)
