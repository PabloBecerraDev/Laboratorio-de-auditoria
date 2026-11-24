import json
import os
from datetime import datetime

from flask import request

from app.extensions import db
from app.models import AuditLog

LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")
AUTH_LOG_PATH = os.path.join(LOG_DIR, "auth_portal.log")


def _append_auth_log(entry: dict):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(AUTH_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_auth_event(username: str, resultado: str, detalle: str = ""):
    """Bitacora de autenticacion (A9.4 - log-on seguro)."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sistema": "portal-principal",
        "usuario": username,
        "resultado": resultado,
        "ip_origen": request.remote_addr if request else None,
        "detalle": detalle,
    }
    _append_auth_log(entry)


def log_audit_event(actor_id, accion, objeto="", detalle=""):
    """Bitacora de auditoria de cambios de permisos (A9.2 / A5.15)."""
    entry = AuditLog(
        actor_id=actor_id,
        accion=accion,
        objeto=objeto,
        detalle=detalle,
        ip_origen=request.remote_addr if request else None,
    )
    db.session.add(entry)
    db.session.commit()
