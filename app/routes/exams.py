"""Examination session and registration routes blueprint (Phase 5)."""

from flask import Blueprint

exams_bp = Blueprint("exams", __name__, url_prefix="/exams")
