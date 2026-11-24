import secrets

import pyotp
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.audit import log_audit_event
from app.extensions import bcrypt, db
from app.models import ROLES, ROLES_CON_MFA_OBLIGATORIO, User
from app.rbac import requires_role

bp = Blueprint("admin_usuarios", __name__, url_prefix="/admin/usuarios")


@bp.route("/")
@login_required
@requires_role("administrador_seguridad", "ti", "direccion")
def listar():
    usuarios = User.query.order_by(User.area, User.nombre_completo).all()
    return render_template("admin_usuarios/list.html", usuarios=usuarios)


@bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@requires_role("administrador_seguridad")
def nuevo():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        nombre_completo = request.form.get("nombre_completo", "").strip()
        email = request.form.get("email", "").strip().lower()
        area = request.form.get("area", "").strip()
        cargo = request.form.get("cargo", "").strip()
        rol = request.form.get("rol", "")

        if rol not in ROLES:
            flash("Rol invalido.", "error")
            return render_template("admin_usuarios/nuevo.html", roles=ROLES)

        if User.query.filter_by(username=username).first():
            flash("Ya existe un usuario con ese username.", "error")
            return render_template("admin_usuarios/nuevo.html", roles=ROLES)

        temp_password = secrets.token_urlsafe(9)
        nuevo_usuario = User(
            username=username,
            nombre_completo=nombre_completo,
            email=email,
            area=area,
            cargo=cargo,
            rol=rol,
            password_hash=bcrypt.generate_password_hash(temp_password).decode("utf-8"),
        )
        if rol in ROLES_CON_MFA_OBLIGATORIO:
            nuevo_usuario.mfa_secret = pyotp.random_base32()

        db.session.add(nuevo_usuario)
        db.session.commit()

        log_audit_event(
            current_user.id,
            "USUARIO_ALTA",
            objeto=f"user:{nuevo_usuario.username}",
            detalle=f"Alta de usuario con rol '{rol}' en area '{area}' (A9.2.1)",
        )

        flash(
            f"Usuario '{username}' creado. Clave temporal: {temp_password}"
            + (f" | Secreto MFA: {nuevo_usuario.mfa_secret}" if nuevo_usuario.mfa_secret else ""),
            "success",
        )
        return redirect(url_for("admin_usuarios.listar"))

    return render_template("admin_usuarios/nuevo.html", roles=ROLES)


@bp.route("/<int:user_id>/editar", methods=["GET", "POST"])
@login_required
@requires_role("administrador_seguridad")
def editar(user_id):
    usuario = User.query.get_or_404(user_id)

    if request.method == "POST":
        rol_anterior = usuario.rol
        nuevo_rol = request.form.get("rol", usuario.rol)
        nueva_area = request.form.get("area", usuario.area)
        nuevo_cargo = request.form.get("cargo", usuario.cargo)

        if nuevo_rol not in ROLES:
            flash("Rol invalido.", "error")
            return render_template("admin_usuarios/editar.html", usuario=usuario, roles=ROLES)

        usuario.rol = nuevo_rol
        usuario.area = nueva_area
        usuario.cargo = nuevo_cargo

        if nuevo_rol in ROLES_CON_MFA_OBLIGATORIO and not usuario.mfa_secret:
            usuario.mfa_secret = pyotp.random_base32()

        db.session.commit()

        if rol_anterior != nuevo_rol:
            log_audit_event(
                current_user.id,
                "USUARIO_CAMBIO_ROL",
                objeto=f"user:{usuario.username}",
                detalle=f"Rol modificado de '{rol_anterior}' a '{nuevo_rol}' (A9.2.2)",
            )

        flash("Usuario actualizado.", "success")
        return redirect(url_for("admin_usuarios.listar"))

    return render_template("admin_usuarios/editar.html", usuario=usuario, roles=ROLES)


@bp.route("/<int:user_id>/baja", methods=["POST"])
@login_required
@requires_role("administrador_seguridad")
def baja(user_id):
    usuario = User.query.get_or_404(user_id)
    usuario.is_active_account = False
    db.session.commit()

    log_audit_event(
        current_user.id,
        "USUARIO_BAJA",
        objeto=f"user:{usuario.username}",
        detalle="Cuenta desactivada manualmente (A9.2.3)",
    )
    flash(f"Usuario '{usuario.username}' dado de baja.", "success")
    return redirect(url_for("admin_usuarios.listar"))


@bp.route("/<int:user_id>/reactivar", methods=["POST"])
@login_required
@requires_role("administrador_seguridad")
def reactivar(user_id):
    usuario = User.query.get_or_404(user_id)
    usuario.is_active_account = True
    usuario.failed_login_attempts = 0
    usuario.locked_until = None
    db.session.commit()

    log_audit_event(
        current_user.id,
        "USUARIO_REACTIVADO",
        objeto=f"user:{usuario.username}",
        detalle="Cuenta reactivada manualmente",
    )
    flash(f"Usuario '{usuario.username}' reactivado.", "success")
    return redirect(url_for("admin_usuarios.listar"))
