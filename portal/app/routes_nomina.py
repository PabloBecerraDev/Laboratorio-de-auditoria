from flask import Blueprint, render_template
from flask_login import login_required

from app.models import Nomina
from app.rbac import requires_role

bp = Blueprint("nomina", __name__, url_prefix="/nomina")


@bp.route("/")
@login_required
@requires_role("rrhh", "direccion", "finanzas")
def listar():
    registros = Nomina.query.all()
    return render_template("nomina/list.html", registros=registros)
