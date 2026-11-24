from flask import Blueprint, render_template
from flask_login import current_user, login_required

bp = Blueprint("dashboard", __name__)

MODULOS_POR_ROL = {
    "direccion": ["clientes", "nomina", "finanzas", "admin_usuarios", "solicitudes"],
    "ti": ["admin_usuarios", "solicitudes"],
    "administrador_seguridad": ["admin_usuarios", "solicitudes"],
    "rrhh": ["nomina", "solicitudes"],
    "finanzas": ["finanzas", "solicitudes"],
    "comercial": ["clientes", "solicitudes"],
    "operaciones": ["solicitudes"],
}


@bp.route("/")
@login_required
def index():
    modulos = MODULOS_POR_ROL.get(current_user.rol, ["solicitudes"])
    return render_template("dashboard.html", modulos=modulos)
