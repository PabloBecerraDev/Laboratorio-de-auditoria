from datetime import datetime

from flask_login import UserMixin

from app.extensions import db

SCHEMA = "portal"

ROLES = [
    "direccion",
    "ti",
    "administrador_seguridad",
    "rrhh",
    "finanzas",
    "comercial",
    "operaciones",
]

# Rol que, segun el reparto de madurez (A9.2 - privilegios elevados), exige
# segundo factor de autenticacion ademas de la clave.
ROLES_CON_MFA_OBLIGATORIO = {"administrador_seguridad"}

MAX_INTENTOS_FALLIDOS = 5
MINUTOS_BLOQUEO = 15


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = {"schema": SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    nombre_completo = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    area = db.Column(db.String(64), nullable=False)
    cargo = db.Column(db.String(128), nullable=False)
    rol = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    mfa_secret = db.Column(db.String(64), nullable=True)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def is_active(self):
        # Flask-Login: una cuenta desactivada (baja de usuario, A9.2) no debe
        # poder autenticarse aunque la contrasena siga siendo correcta.
        return self.is_active_account

    @property
    def requiere_mfa(self):
        return self.rol in ROLES_CON_MFA_OBLIGATORIO

    def __repr__(self):
        return f"<User {self.username} ({self.rol})>"


class Cliente(db.Model):
    __tablename__ = "clientes"
    __table_args__ = {"schema": SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    nombre_empresa = db.Column(db.String(128), nullable=False)
    nit = db.Column(db.String(32), nullable=False, unique=True)
    contacto_nombre = db.Column(db.String(128), nullable=False)
    contacto_telefono = db.Column(db.String(32), nullable=False)
    contacto_email = db.Column(db.String(128), nullable=False)
    cupo_credito = db.Column(db.Numeric(12, 2), nullable=False)
    comercial_asignado_id = db.Column(
        db.Integer, db.ForeignKey(f"{SCHEMA}.users.id"), nullable=True
    )

    comercial_asignado = db.relationship("User", foreign_keys=[comercial_asignado_id])


class Nomina(db.Model):
    __tablename__ = "nomina"
    __table_args__ = {"schema": SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    empleado_id = db.Column(db.Integer, db.ForeignKey(f"{SCHEMA}.users.id"), nullable=False)
    salario_base = db.Column(db.Numeric(12, 2), nullable=False)
    bonificaciones = db.Column(db.Numeric(12, 2), default=0)
    fecha_ingreso = db.Column(db.Date, nullable=False)
    cuenta_bancaria = db.Column(db.String(32), nullable=False)

    empleado = db.relationship("User", foreign_keys=[empleado_id])


class MovimientoFinanciero(db.Model):
    __tablename__ = "finanzas"
    __table_args__ = {"schema": SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    concepto = db.Column(db.String(255), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    tipo = db.Column(db.String(16), nullable=False)  # ingreso | egreso
    fecha = db.Column(db.Date, nullable=False)
    registrado_por_id = db.Column(db.Integer, db.ForeignKey(f"{SCHEMA}.users.id"))

    registrado_por = db.relationship("User", foreign_keys=[registrado_por_id])


class AuditLog(db.Model):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey(f"{SCHEMA}.users.id"), nullable=True)
    accion = db.Column(db.String(64), nullable=False)
    objeto = db.Column(db.String(255), nullable=True)
    detalle = db.Column(db.Text, nullable=True)
    ip_origen = db.Column(db.String(64), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    actor = db.relationship("User", foreign_keys=[actor_id])


class AccessRequest(db.Model):
    __tablename__ = "access_requests"
    __table_args__ = {"schema": SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    solicitante_id = db.Column(db.Integer, db.ForeignKey(f"{SCHEMA}.users.id"), nullable=False)
    recurso_solicitado = db.Column(db.String(255), nullable=False)
    justificacion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(16), default="pendiente", nullable=False)
    aprobador_id = db.Column(db.Integer, db.ForeignKey(f"{SCHEMA}.users.id"), nullable=True)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)

    solicitante = db.relationship("User", foreign_keys=[solicitante_id])
    aprobador = db.relationship("User", foreign_keys=[aprobador_id])
