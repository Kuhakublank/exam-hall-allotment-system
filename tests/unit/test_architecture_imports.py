"""Smoke tests verifying that every module in the architecture scaffold imports cleanly."""

import importlib
import pytest


SCAFFOLD_MODULES = [
    "app",
    "app.config",
    "app.extensions",
    "app.models",
    "app.models.user",
    "app.models.student",
    "app.models.hall",
    "app.models.exam",
    "app.models.allocation",
    "app.algorithms",
    "app.algorithms.structures",
    "app.algorithms.hall_allotment_ffd",
    "app.algorithms.mrv",
    "app.algorithms.forward_checking",
    "app.algorithms.backtracking",
    "app.algorithms.greedy",
    "app.algorithms.validator",
    "app.algorithms.cpsat_verifier",
    "app.services.auth_service",
    "app.services.import_service",
    "app.services.validation_service",
    "app.services.allocation_service",
    "app.services.report_service",
    "app.routes",
    "app.routes.auth",
    "app.routes.dashboard",
    "app.routes.students",
    "app.routes.subjects",
    "app.routes.exams",
    "app.routes.halls",
    "app.routes.seats",
    "app.routes.constraints",
    "app.routes.allocations",
    "app.routes.reports",
]


@pytest.mark.parametrize("module_path", SCAFFOLD_MODULES)
def test_scaffold_module_imports(module_path):
    """Every architectural module should import cleanly without syntax or circular errors."""
    mod = importlib.import_module(module_path)
    assert mod is not None
