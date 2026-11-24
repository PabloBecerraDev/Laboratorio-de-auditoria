"""
Portal legacy de proveedores de Nortia Distribuciones S.A.S.

Heredado de la fusion con un distribuidor regional hace 4 anios. Nunca se
migro al mismo esquema de gobierno de accesos que el portal principal.
Implementa, A PROPOSITO, el lado "brecha" del reparto de madurez en
CONTROLES.md:

  - Hash de contrasena MD5 sin sal (A9.4 - calidad/gestion de contrasenas).
  - Sin bloqueo por intentos fallidos ni MFA (A9.4 - log-on seguro).
  - Cuenta generica "soporte" compartida por varios colaboradores (A9.4 -
    cuentas nominativas).
  - Password reutilizada entre este sistema y el laboratorio SSH (higiene
    de credenciales, A9.3).

Esto es laboratorio educativo. NO reutilizar este patron en sistemas reales.
"""
import hashlib
import json
import os
import time
from datetime import datetime

import psycopg2
from flask import Flask, redirect, render_template_string, request, session, url_for

DATABASE_URL = os.environ.get("DATABASE_URL")
LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")
AUTH_LOG_PATH = os.path.join(LOG_DIR, "auth_legacy.log")

app = Flask(__name__)
app.secret_key = "legacy-secret-nunca-rotada"  # intencional: higiene de secretos pobre en el legacy

LOGIN_TEMPLATE = """
<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Portal de Proveedores (legacy)</title>
<style>
body{font-family:Tahoma,Arial,sans-serif;background:#e8e8e8;margin:0;}
.banner{background:#b23b3b;color:#fff;text-align:center;padding:6px;font-size:0.8rem;font-weight:bold;}
.box{max-width:340px;margin:60px auto;background:#fff;padding:24px;border:1px solid #bbb;}
h2{color:#333;margin-top:0;}
input{width:100%;padding:8px;margin:6px 0 14px;border:1px solid #aaa;}
button{background:#555;color:#fff;border:none;padding:8px 16px;cursor:pointer;}
.error{color:#a12f2f;font-size:0.9rem;}
.note{color:#777;font-size:0.75rem;margin-top:20px;}
</style></head>
<body>
<div class="banner">PORTAL LEGACY DE PROVEEDORES — LABORATORIO VULNERABLE — SOLO 127.0.0.1</div>
<div class="box">
<h2>Portal de Proveedores (version 2019)</h2>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="post">
<input type="text" name="username" placeholder="Usuario" required>
<input type="password" name="password" placeholder="Contrasena" required>
<button type="submit">Ingresar</button>
</form>
<p class="note">Sistema heredado de la fusion de 2020. Pendiente de migracion al portal principal.</p>
</div>
</body></html>
"""

DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Portal de Proveedores</title>
<style>body{font-family:Tahoma,Arial,sans-serif;background:#e8e8e8;}
.banner{background:#b23b3b;color:#fff;text-align:center;padding:6px;font-size:0.8rem;font-weight:bold;}
.box{max-width:500px;margin:40px auto;background:#fff;padding:24px;border:1px solid #bbb;}
a{color:#555;}</style></head>
<body>
<div class="banner">PORTAL LEGACY DE PROVEEDORES — LABORATORIO VULNERABLE — SOLO 127.0.0.1</div>
<div class="box">
<h2>Bienvenido, {{ nombre }}</h2>
<p>NIT asociado: {{ nit }}</p>
<p>Modulo de pedidos y facturas electronicas (fuera de alcance de este laboratorio).</p>
<a href="{{ url_for('logout') }}">Cerrar sesion</a>
</div>
</body></html>
"""

USUARIOS_SEMILLA = [
    # username, password_en_claro, nombre_proveedor, nit
    ("distrinorte", "distrinorte2024", "Distribuidora del Norte SAS", "800111222-1"),
    ("proveequipos", "proveequipos1", "Proveequipos del Cauca", "800222333-2"),
    ("insuval", "insuval123", "Insumos del Valle Ltda", "800333444-3"),
    ("textilpacifico", "qwerty123", "Textiles del Pacifico SAS", "800444555-4"),
    ("logisticasur", "12345678", "Logistica del Sur SAS", "800555666-5"),
    ("comercialandes", "comercialandes", "Comercial Andes SAS", "800666777-6"),
    ("empacasplus", "empacas2023", "Empaques Plus SAS", "800777888-7"),
    # Cuenta generica compartida por el equipo de soporte del integrador (brecha #18).
    ("soporte", "soporte2024", "Soporte Tecnico Integrador (cuenta compartida)", "N/A"),
]


def md5(texto: str) -> str:
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def get_conn():
    return psycopg2.connect(DATABASE_URL, options="-c search_path=legacy")


def esperar_db():
    for intento in range(30):
        try:
            conn = get_conn()
            conn.close()
            return
        except psycopg2.OperationalError:
            print(f"[legacy] esperando a Postgres... intento {intento+1}")
            time.sleep(2)
    raise RuntimeError("Postgres no disponible")


def inicializar():
    esperar_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios_proveedores (
            id SERIAL PRIMARY KEY,
            username VARCHAR(64) UNIQUE NOT NULL,
            password_md5 VARCHAR(32) NOT NULL,
            nombre_proveedor VARCHAR(128) NOT NULL,
            nit VARCHAR(32) NOT NULL
        );
        """
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM usuarios_proveedores;")
    (total,) = cur.fetchone()
    if total == 0:
        for username, password, proveedor, nit in USUARIOS_SEMILLA:
            cur.execute(
                "INSERT INTO usuarios_proveedores (username, password_md5, nombre_proveedor, nit) "
                "VALUES (%s, %s, %s, %s)",
                (username, md5(password), proveedor, nit),
            )
        conn.commit()
        print("[legacy] Usuarios de proveedores sembrados.")
    cur.close()
    conn.close()


def log_evento(username, resultado, detalle=""):
    os.makedirs(LOG_DIR, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sistema": "portal-legacy-proveedores",
        "usuario": username,
        "resultado": resultado,
        "ip_origen": request.remote_addr,
        "detalle": detalle,
    }
    with open(AUTH_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        conn = get_conn()
        cur = conn.cursor()
        # Nota: sin bloqueo por intentos fallidos ni limite de tasa (brecha #15).
        cur.execute(
            "SELECT nombre_proveedor, nit FROM usuarios_proveedores "
            "WHERE username = %s AND password_md5 = %s",
            (username, md5(password)),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            session["username"] = username
            session["nombre_proveedor"] = row[0]
            session["nit"] = row[1]
            log_evento(username, "SUCCESS")
            return redirect(url_for("dashboard"))

        log_evento(username, "FAILED")
        return render_template_string(LOGIN_TEMPLATE, error="Usuario o contrasena incorrectos.")

    return render_template_string(LOGIN_TEMPLATE, error=None)


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template_string(
        DASHBOARD_TEMPLATE, nombre=session["nombre_proveedor"], nit=session["nit"]
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    inicializar()
    app.run(host="0.0.0.0", port=5001, debug=False)
