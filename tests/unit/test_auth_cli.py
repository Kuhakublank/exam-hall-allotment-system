"""Phase 2 tests for Flask CLI initial administrator creation and duplicate prevention."""

from app.models import User


def test_create_admin_cli_success(app):
    """CLI create-admin should create a hashed admin account with role='admin'."""
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "create-admin",
            "--username",
            "chief_admin",
            "--email",
            "Admin@University.EDU",
            "--password",
            "SecurePass#2026",
        ]
    )

    assert result.exit_code == 0
    assert "Created administrator 'chief_admin'" in result.output

    created = User.query.filter_by(email="admin@university.edu").first()
    assert created is not None
    assert created.role == "admin"
    assert created.is_active is True
    assert created.password_hash != "SecurePass#2026"
    assert created.check_password("SecurePass#2026") is True


def test_create_admin_cli_interactive_prompts(app):
    """CLI create-admin should prompt interactively when flags/env vars are omitted."""
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin"],
        input="prompt_admin\nprompt@university.edu\nStrongPass!99\nStrongPass!99\n",
    )

    assert result.exit_code == 0
    created = User.query.filter_by(email="prompt@university.edu").first()
    assert created is not None
    assert created.username == "prompt_admin"
    assert created.role == "admin"


def test_create_admin_prevents_duplicate_email_and_username(app):
    """CLI create-admin must reject duplicate admin accounts cleanly."""
    runner = app.test_cli_runner()
    first = runner.invoke(
        args=[
            "create-admin",
            "--username",
            "admin1",
            "--email",
            "admin1@university.edu",
            "--password",
            "SecurePass#2026",
        ]
    )
    assert first.exit_code == 0

    dup_email = runner.invoke(
        args=[
            "create-admin",
            "--username",
            "admin2",
            "--email",
            "admin1@university.edu",
            "--password",
            "AnotherPass#2026",
        ]
    )
    assert dup_email.exit_code != 0
    assert "already exists" in dup_email.output

    dup_username = runner.invoke(
        args=[
            "create-admin",
            "--username",
            "admin1",
            "--email",
            "admin2@university.edu",
            "--password",
            "AnotherPass#2026",
        ]
    )
    assert dup_username.exit_code != 0
    assert "already exists" in dup_username.output
    assert User.query.count() == 1
