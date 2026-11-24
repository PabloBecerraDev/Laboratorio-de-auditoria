from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from app.models import Cliente
from app.rbac import requires_role

bp = Blueprint("clientes", __name__, url_prefix="/clientes")


@bp.route("/")
@login_required
@requires_role("comercial", "direccion")
def listar():
    if current_user.rol == "comercial":
        clientes = Cliente.query.filter_by(comercial_asignado_id=current_user.id).all()
    else:
        clientes = Cliente.query.all()
    return render_template("clientes/list.html", clientes=clientes)


@bp.route("/<int:cliente_id>")
@login_required
@requires_role("comercial", "direccion")
def detalle(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)

    # --- BRECHA DELIBERADA DEL LABORATORIO (control de acceso a nivel de objeto) ---
    # El decorador @requires_role ya valido que el rol pueda entrar al modulo
    # Clientes, pero aqui falta el segundo chequeo: que ESTE cliente pertenezca
    # a la cartera del comercial autenticado. Un usuario con rol "comercial"
    # puede ver cualquier ficha de cliente incrementando el ID en la URL,
    # aunque no este asignado a el. Es la brecha #20 de CONTROLES.md
    # (A5.15 / A9.4 - granularidad de control de acceso a nivel de registro,
    # detectable con ZAP/Burp mediante fuzzing de IDs secuenciales).
    #
    # Una implementacion correcta anadiria aqui:
    #   if current_user.rol == "comercial" and cliente.comercial_asignado_id != current_user.id:
    #       abort(403)

    return render_template("clientes/detail.html", cliente=cliente)
