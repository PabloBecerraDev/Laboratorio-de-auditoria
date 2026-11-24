from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.audit import log_audit_event
from app.extensions import db
from app.models import AccessRequest
from app.rbac import requires_role

bp = Blueprint("solicitudes", __name__, url_prefix="/solicitudes")


@bp.route("/")
@login_required
def listar():
    if current_user.rol == "administrador_seguridad":
        solicitudes = AccessRequest.query.order_by(AccessRequest.fecha_solicitud.desc()).all()
    else:
        solicitudes = (
            AccessRequest.query.filter_by(solicitante_id=current_user.id)
            .order_by(AccessRequest.fecha_solicitud.desc())
            .all()
        )
    return render_template("solicitudes/list.html", solicitudes=solicitudes)


@bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva():
    if request.method == "POST":
        recurso = request.form.get("recurso_solicitado", "").strip()
        justificacion = request.form.get("justificacion", "").strip()

        solicitud = AccessRequest(
            solicitante_id=current_user.id,
            recurso_solicitado=recurso,
            justificacion=justificacion,
        )
        db.session.add(solicitud)
        db.session.commit()

        log_audit_event(
            current_user.id,
            "SOLICITUD_ACCESO_CREADA",
            objeto=f"solicitud:{solicitud.id}",
            detalle=f"Recurso solicitado: {recurso}",
        )
        flash("Solicitud enviada al administrador de seguridad.", "success")
        return redirect(url_for("solicitudes.listar"))

    return render_template("solicitudes/nueva.html")


@bp.route("/<int:solicitud_id>/resolver", methods=["POST"])
@login_required
@requires_role("administrador_seguridad")
def resolver(solicitud_id):
    solicitud = AccessRequest.query.get_or_404(solicitud_id)
    decision = request.form.get("decision")

    if decision not in ("aprobada", "rechazada"):
        flash("Decision invalida.", "error")
        return redirect(url_for("solicitudes.listar"))

    solicitud.estado = decision
    solicitud.aprobador_id = current_user.id
    solicitud.fecha_resolucion = datetime.utcnow()
    db.session.commit()

    log_audit_event(
        current_user.id,
        "SOLICITUD_ACCESO_RESUELTA",
        objeto=f"solicitud:{solicitud.id}",
        detalle=f"Decision: {decision} (A9.2 - gestion del ciclo de vida de accesos)",
    )
    flash(f"Solicitud #{solicitud.id} marcada como {decision}.", "success")
    return redirect(url_for("solicitudes.listar"))
