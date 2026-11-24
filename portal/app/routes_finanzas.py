from flask import Blueprint, render_template
from flask_login import login_required

from app.models import MovimientoFinanciero
from app.rbac import requires_role

bp = Blueprint("finanzas", __name__, url_prefix="/finanzas")


@bp.route("/")
@login_required
@requires_role("finanzas", "direccion")
def listar():
    movimientos = MovimientoFinanciero.query.order_by(MovimientoFinanciero.fecha.desc()).all()
    return render_template("finanzas/list.html", movimientos=movimientos)
