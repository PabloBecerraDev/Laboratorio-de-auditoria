"""
Script de semilla del portal principal de Nortia Distribuciones S.A.S.
Crea ~21 usuarios ficticios (organigrama completo), clientes, nomina,
movimientos financieros, solicitudes de acceso de ejemplo y un log de
firewall simulado para la medicion de A9.4.

Idempotente: si ya hay usuarios, no vuelve a sembrar.
"""
import os
import random
from datetime import date, datetime, timedelta

import pyotp

from app import create_app
from app.extensions import bcrypt, db
from app.models import AccessRequest, AuditLog, Cliente, MovimientoFinanciero, Nomina, User

DEMO_PASSWORD = "Nortia#2024"

# username, nombre_completo, email, area, cargo, rol, notas
USUARIOS = [
    ("msalcedo", "Mariana Salcedo Vidal", "msalcedo@nortia.co", "Direccion General", "Gerente General", "direccion"),
    ("cortiz", "Camila Andrea Ortiz", "cortiz@nortia.co", "Seguridad de la Informacion", "Oficial de Seguridad de la Informacion", "direccion"),
    ("fguzman", "Felipe Guzman Mora", "fguzman@nortia.co", "Seguridad de la Informacion", "Administrador de Seguridad", "administrador_seguridad"),
    ("jrengifo", "Julian Esteban Rengifo", "jrengifo@nortia.co", "TI", "Jefe de TI", "ti"),
    ("cjimenez", "Camilo Jimenez Ruiz", "cjimenez@nortia.co", "TI", "Desarrollador", "ti"),
    ("sgomez", "Sebastian Gomez Leon", "sgomez@nortia.co", "TI", "Desarrollador", "ti"),
    ("lpaz", "Luisa Paz Hurtado", "lpaz@nortia.co", "TI", "Analista de Infraestructura", "ti"),
    ("dpena", "Diana Carolina Pena", "dpena@nortia.co", "Recursos Humanos", "Jefe de RRHH", "rrhh"),
    ("vcastro", "Valentina Castro Nino", "vcastro@nortia.co", "Recursos Humanos", "Analista de RRHH", "rrhh"),
    ("alondono", "Andres Felipe Londono", "alondono@nortia.co", "Finanzas", "Jefe de Finanzas", "finanzas"),
    ("jmoreno", "Jorge Moreno Diaz", "jmoreno@nortia.co", "Finanzas", "Analista de Finanzas", "finanzas"),
    ("jgarcia", "Juan David Garcia", "jgarcia@nortia.co", "Comercial", "Ejecutivo Comercial", "comercial"),
    ("msuarez", "Maria Fernanda Suarez", "msuarez@nortia.co", "Comercial", "Ejecutiva Comercial", "comercial"),
    ("rortiz", "Ricardo Ortiz Mena", "rortiz@nortia.co", "Comercial", "Ejecutivo Comercial", "comercial"),
    ("ntorres", "Natalia Torres Gil", "ntorres@nortia.co", "Comercial", "Ejecutiva Comercial", "comercial"),
    ("lcorrea", "Laura Ximena Correa", "lcorrea@nortia.co", "Operaciones", "Jefe de Operaciones", "operaciones"),
    ("kherrera", "Katherine Herrera Soto", "kherrera@nortia.co", "Operaciones", "Coordinadora de Bodega", "operaciones"),
    ("dvargas", "David Vargas Pinzon", "dvargas@nortia.co", "Operaciones", "Coordinador Logistico", "operaciones"),
    ("fmartinez", "Fabian Martinez Cuesta", "fmartinez@nortia.co", "Operaciones", "Auxiliar de Bodega", "operaciones"),
    # --- Evidencia deliberada de brechas A9.2.3 / A5.15 (mínimo privilegio) ---
    ("aherrera", "Andrea Herrera Londono", "aherrera@nortia.co", "Comercial",
     "Ex-Ejecutiva Comercial (retirada hace 3 meses — cuenta NUNCA desactivada, evidencia brecha #7 A9.2.3)",
     "comercial"),
    ("jrios", "Jonathan Rios Beltran", "jrios@nortia.co", "TI",
     "Ex-practicante de TI (permisos de rol 'ti' nunca revocados tras fin de practicas, evidencia brecha #4 A5.15 minimo privilegio)",
     "ti"),
]

CLIENTES = [
    ("Ferreteria El Tornillo Feliz SAS", "900123456-1", "Oscar Daza", "3001112233", "compras@tornillofeliz.co", 15000000),
    ("Aseo Total del Valle Ltda", "900234567-2", "Patricia Lenis", "3002223344", "gerencia@aseototal.co", 8000000),
    ("Distribuciones JyM del Pacifico", "900345678-3", "Jaime Mosquera", "3003334455", "jaime@jym.co", 22000000),
    ("Supermercados La Economia SAS", "900456789-4", "Carolina Victoria", "3004445566", "compras@laeconomia.co", 35000000),
    ("Hogar y Ferreteria Dos Rios", "900567890-5", "Hernan Bonilla", "3005556677", "hernan@dosrios.co", 12000000),
    ("Insumos Industriales Palmira SAS", "900678901-6", "Liliana Castano", "3006667788", "liliana@industrialespalmira.co", 40000000),
    ("Comercializadora El Buen Precio", "900789012-7", "Freddy Imbachi", "3007778899", "fredy@elbuenprecio.co", 9000000),
    ("Aseo Profesional Andino", "900890123-8", "Monica Zapata", "3008889900", "monica@aseoandino.co", 11000000),
    ("Ferreteria Dos Hermanos Cali", "900901234-9", "Gustavo Trochez", "3009990011", "gustavo@doshermanos.co", 6000000),
    ("Mayoristas del Suroccidente SAS", "901012345-0", "Adriana Fory", "3010001122", "adriana@mayosur.co", 50000000),
    ("Ferreteria La Esquina Jamundi", "901123456-1", "Wilson Sanclemente", "3011112233", "wilson@laesquina.co", 7500000),
    ("Distribuidora Aseo Norte", "901234567-2", "Claudia Potes", "3012223344", "claudia@aseonorte.co", 13000000),
]

ESTADO_LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")


def generar_log_firewall():
    os.makedirs(ESTADO_LOG_DIR, exist_ok=True)
    path = os.path.join(ESTADO_LOG_DIR, "firewall_simulado.log")
    if os.path.exists(path):
        return
    acciones = ["ALLOW", "ALLOW", "ALLOW", "DENY"]
    clasif = ["insignificante", "insignificante", "preocupante", "critico"]
    base = datetime.utcnow() - timedelta(days=7)
    lineas = []
    for i in range(400):
        ts = base + timedelta(minutes=i * 25)
        ip = f"192.168.{random.randint(10,40)}.{random.randint(2,250)}"
        puerto = random.choice([80, 443, 22, 5432, 5000, 5001])
        accion = random.choice(acciones)
        c = random.choice(clasif) if accion == "DENY" else "insignificante"
        lineas.append(
            f"{ts.isoformat()}Z src={ip} dst_port={puerto} accion={accion} clasificacion={c}"
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    print(f"[seed] Log de firewall simulado generado en {path}")


def run():
    app = create_app()
    with app.app_context():
        if User.query.first() is not None:
            print("[seed] Ya existen usuarios, se omite la siembra.")
            generar_log_firewall()
            return

        usuarios_creados = {}
        for username, nombre, email, area, cargo, rol in USUARIOS:
            u = User(
                username=username,
                nombre_completo=nombre,
                email=email,
                area=area,
                cargo=cargo,
                rol=rol,
                password_hash=bcrypt.generate_password_hash(DEMO_PASSWORD).decode("utf-8"),
            )
            if rol == "administrador_seguridad":
                u.mfa_secret = pyotp.random_base32()
            db.session.add(u)
            usuarios_creados[username] = u
        db.session.commit()

        comerciales = ["jgarcia", "msuarez", "rortiz", "ntorres"]
        for i, (nombre_empresa, nit, contacto, tel, mail, cupo) in enumerate(CLIENTES):
            comercial = usuarios_creados[comerciales[i % len(comerciales)]]
            db.session.add(
                Cliente(
                    nombre_empresa=nombre_empresa,
                    nit=nit,
                    contacto_nombre=contacto,
                    contacto_telefono=tel,
                    contacto_email=mail,
                    cupo_credito=cupo,
                    comercial_asignado_id=comercial.id,
                )
            )
        db.session.commit()

        for username, u in usuarios_creados.items():
            db.session.add(
                Nomina(
                    empleado_id=u.id,
                    salario_base=random.randint(14, 45) * 100000,
                    bonificaciones=random.choice([0, 100000, 200000, 350000]),
                    fecha_ingreso=date(2021, 1, 1) + timedelta(days=random.randint(0, 1400)),
                    cuenta_bancaria=f"BANCOL-{random.randint(10000000,99999999)}",
                )
            )
        db.session.commit()

        conceptos = [
            ("Venta mayorista Supermercados La Economia", "ingreso", 18000000),
            ("Pago nomina quincenal", "egreso", 95000000),
            ("Compra insumos proveedor nacional", "egreso", 42000000),
            ("Venta Distribuciones JyM", "ingreso", 11000000),
            ("Pago arriendo bodega", "egreso", 6500000),
            ("Venta Mayoristas del Suroccidente", "ingreso", 25000000),
            ("Pago servicios publicos", "egreso", 3200000),
            ("Venta Ferreteria El Tornillo Feliz", "ingreso", 7200000),
            ("Pago licencias software", "egreso", 4800000),
            ("Venta Insumos Industriales Palmira", "ingreso", 31000000),
        ]
        fin_user = usuarios_creados["alondono"]
        for i, (concepto, tipo, monto) in enumerate(conceptos):
            db.session.add(
                MovimientoFinanciero(
                    concepto=concepto,
                    monto=monto,
                    tipo=tipo,
                    fecha=date.today() - timedelta(days=i * 3),
                    registrado_por_id=fin_user.id,
                )
            )
        db.session.commit()

        # Solicitudes de acceso de ejemplo (A9.2 - ciclo de vida de accesos).
        seg = usuarios_creados["fguzman"]
        ej1 = AccessRequest(
            solicitante_id=usuarios_creados["jmoreno"].id,
            recurso_solicitado="Modulo Clientes - solo lectura",
            justificacion="Necesito validar cupos de credito contra cartera para el cierre contable.",
            estado="aprobada",
            aprobador_id=seg.id,
            fecha_resolucion=datetime.utcnow() - timedelta(days=2),
        )
        ej2 = AccessRequest(
            solicitante_id=usuarios_creados["kherrera"].id,
            recurso_solicitado="Modulo Finanzas - solo lectura",
            justificacion="Para conciliar despachos con facturacion.",
            estado="pendiente",
        )
        db.session.add_all([ej1, ej2])
        db.session.commit()

        # Historico de auditoria previo a la entrega del laboratorio.
        db.session.add_all([
            AuditLog(actor_id=seg.id, accion="USUARIO_ALTA", objeto="user:jrios",
                     detalle="Alta de practicante TI (A9.2.1)",
                     timestamp=datetime.utcnow() - timedelta(days=200)),
            AuditLog(actor_id=seg.id, accion="USUARIO_ALTA", objeto="user:aherrera",
                     detalle="Alta ejecutiva comercial (A9.2.1)",
                     timestamp=datetime.utcnow() - timedelta(days=260)),
        ])
        db.session.commit()

        generar_log_firewall()

        print("[seed] Siembra completa.")
        print(f"[seed] Password de demo para todos los usuarios: {DEMO_PASSWORD}")
        print(f"[seed] Secreto MFA de fguzman (administrador_seguridad): {usuarios_creados['fguzman'].mfa_secret}")


if __name__ == "__main__":
    run()
