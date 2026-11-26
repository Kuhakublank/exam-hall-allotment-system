"""Authentication routes blueprint (login and logout)."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField
from wtforms.validators import DataRequired

from app.services.auth_service import authenticate_admin, is_safe_redirect_url

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class LoginForm(FlaskForm):
    """CSRF-protected administrator login form."""

    email = EmailField("Email Address", validators=[DataRequired(message="Email is required.")])
    password = PasswordField("Password", validators=[DataRequired(message="Password is required.")])


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an administrator using email and password."""
    if current_user.is_authenticated and getattr(current_user, "role", None) == "admin":
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_admin(form.email.data, form.password.data)
        if user is None:
            # Uniform message so unknown emails cannot be enumerated
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", form=form), 401

        login_user(user)
        session.permanent = True
        flash("Signed in successfully.", "success")

        next_url = request.args.get("next") or request.form.get("next")
        if is_safe_redirect_url(next_url):
            return redirect(next_url)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html", form=form)


@auth_bp.post("/logout")
@login_required
def logout():
    """Terminate the current authenticated session securely."""
    logout_user()
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
