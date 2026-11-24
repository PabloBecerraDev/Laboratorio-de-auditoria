from datetime import datetime, timedelta

import pyotp
from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from flask_login import current_user, login_required, login_user, logout_user

from app.audit import log_audit_event, log_auth_event
from app.extensions import bcrypt, db
from app.models import MAX_INTENTOS_FALLIDOS, MINUTOS_BLOQUEO, User

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        # Mensaje generico: no revelamos si el usuario existe o no (log-on seguro, A9.4).
        error_generico = "Usuario o contrasena incorrectos."

        if user is None:
            log_auth_event(username, "FAILED", "usuario inexistente")
            flash(error_generico, "error")
            return render_template("login.html")

        if user.locked_until and user.locked_until > datetime.utcnow():
            minutos_restantes = int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1
            log_auth_event(username, "BLOCKED", f"cuenta bloqueada, faltan {minutos_restantes} min")
            flash(f"Cuenta bloqueada temporalmente. Intenta de nuevo en {minutos_restantes} minuto(s).", "error")
            return render_template("login.html")

        if not user.is_active_account:
            log_auth_event(username, "FAILED", "cuenta inactiva (dada de baja)")
            flash(error_generico, "error")
            return render_template("login.html")

        if not bcrypt.check_password_hash(user.password_hash, password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_INTENTOS_FALLIDOS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=MINUTOS_BLOQUEO)
                log_auth_event(username, "LOCKED", f"{MAX_INTENTOS_FALLIDOS} intentos fallidos consecutivos")
            else:
                log_auth_event(
                    username,
                    "FAILED",
                    f"contrasena incorrecta (intento {user.failed_login_attempts}/{MAX_INTENTOS_FALLIDOS})",
                )
            db.session.commit()
            flash(error_generico, "error")
            return render_template("login.html")

        # Credenciales correctas.
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()

        if user.requiere_mfa:
            session["mfa_pending_user_id"] = user.id
            log_auth_event(username, "PASSWORD_OK_MFA_PENDING", "segundo factor requerido")
            return redirect(url_for("auth.mfa"))

        user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user)
        log_auth_event(username, "SUCCESS", "login sin MFA")
        return redirect(url_for("dashboard.index"))

    return render_template("login.html")


@bp.route("/mfa", methods=["GET", "POST"])
def mfa():
    user_id = session.get("mfa_pending_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if user is None:
        session.pop("mfa_pending_user_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(codigo, valid_window=1):
            session.pop("mfa_pending_user_id", None)
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            log_auth_event(user.username, "SUCCESS", "login con MFA")
            return redirect(url_for("dashboard.index"))

        log_auth_event(user.username, "MFA_FAILED", "codigo TOTP invalido")
        flash("Codigo de verificacion invalido.", "error")

    return render_template("mfa.html", username=user.username)


@bp.route("/logout")
@login_required
def logout():
    log_auth_event(current_user.username, "LOGOUT", "")
    logout_user()
    return redirect(url_for("auth.login"))
