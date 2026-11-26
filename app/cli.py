"""Flask CLI commands for secure administrative setup."""

import os
import click
from flask import Flask
from flask.cli import with_appcontext

from app.services.auth_service import create_admin_user


@click.command("create-admin")
@click.option("--username", default=None, help="Admin username (or set ADMIN_USERNAME).")
@click.option("--email", default=None, help="Admin email (or set ADMIN_EMAIL).")
@click.option("--password", default=None, help="Admin password (or set ADMIN_PASSWORD).")
@with_appcontext
def create_admin_command(username: str | None, email: str | None, password: str | None) -> None:
    """Create an initial administrator account securely without hardcoded defaults."""
    resolved_username = username or os.environ.get("ADMIN_USERNAME")
    resolved_email = email or os.environ.get("ADMIN_EMAIL")
    resolved_password = password or os.environ.get("ADMIN_PASSWORD")

    if not resolved_username:
        resolved_username = click.prompt("Administrator username", type=str)
    if not resolved_email:
        resolved_email = click.prompt("Administrator email", type=str)
    if not resolved_password:
        resolved_password = click.prompt(
            "Administrator password (min 8 chars)",
            hide_input=True,
            confirmation_prompt=True,
            type=str,
        )

    try:
        admin = create_admin_user(resolved_username, resolved_email, resolved_password)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Created administrator '{admin.username}' ({admin.email}) with role '{admin.role}'.")


def register_cli_commands(flask_app: Flask) -> None:
    """Register custom Flask CLI commands on the application."""
    flask_app.cli.add_command(create_admin_command)
