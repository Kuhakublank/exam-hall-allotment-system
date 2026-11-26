"""Admin dashboard and settings routes blueprint."""

from datetime import date
from flask import Blueprint, render_template

from app.models import AllocationRun, ExamSession, Hall, Student, Subject
from app.services.auth_service import admin_required

dashboard_bp = Blueprint("dashboard", __name__)


def render_module_placeholder(
    module_name: str,
    phase_label: str,
    description: str,
    active_nav: str,
):
    """Render an honest protected placeholder page for upcoming phases."""
    return render_template(
        "dashboard/module_placeholder.html",
        module_name=module_name,
        phase_label=phase_label,
        description=description,
        active_nav=active_nav,
    )


@dashboard_bp.get("/")
@dashboard_bp.get("/dashboard")
@admin_required
def index():
    """Render the administration dashboard using live database statistics."""
    stats = {
        "total_students": Student.query.count(),
        "total_halls": Hall.query.count(),
        "total_subjects": Subject.query.count(),
        "total_sessions": ExamSession.query.count(),
    }

    upcoming_exams = (
        ExamSession.query.filter(ExamSession.exam_date >= date.today())
        .order_by(ExamSession.exam_date.asc(), ExamSession.start_time.asc())
        .limit(5)
        .all()
    )

    recent_allocations = (
        AllocationRun.query.order_by(AllocationRun.created_at.desc()).limit(5).all()
    )

    return render_template(
        "dashboard/index.html",
        stats=stats,
        upcoming_exams=upcoming_exams,
        recent_allocations=recent_allocations,
        active_nav="dashboard",
    )


@dashboard_bp.get("/settings")
@admin_required
def settings():
    """Protected placeholder view for system settings."""
    return render_module_placeholder(
        module_name="Settings",
        phase_label="Planned Configuration",
        description="System-wide defaults and account management options will be expanded in later phases.",
        active_nav="settings",
    )
