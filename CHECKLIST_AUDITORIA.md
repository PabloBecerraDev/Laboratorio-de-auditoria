# CHECKLIST_AUDITORIA.md — Checklist de ejecución para recolectar evidencia
## Nortia Distribuciones S.A.S. — laboratorio académico

> ⚠️ Solo contra este laboratorio local (`127.0.0.1` / contenedor `nortia-kali`).
> Ver `README.md` (cómo levantarlo), `CONTROLES.md` (el guion normativo con
> pesos, amenazas MAGERIT y scores) y `GUIA_AUDITORIA_KALI.md` (explicación
> técnica y comandos extendidos). Este archivo es la lista de tareas en
> orden, lista para ir marcando mientras ejecutan.

## 0. Antes de empezar

Usa las 3 terminales descritas antes: **T1** = control (host), **T2** =
`docker exec -it nortia-kali bash`, **T3** = logs en vivo.

- [ ] **T1** — confirmar que todo está arriba:
  ```powershell
  docker compose ps
  ```
- [ ] **T1** — carpeta de evidencias (ya creada en `evidencias/A5.15`,
  `A9.2`, `A9.3`, `A9.4`, con un `.txt` vacío por cada ítem de este
  checklist, listo para llenar):
  ```powershell
  Get-ChildItem -Recurse evidencias
  ```
- [ ] **T3** — dejar los logs corriendo de fondo:
  ```powershell
  docker compose logs -f portal legacy
  ```

Cada ítem abajo dice **dónde** correrlo, **qué comando**, **qué deberías
ver**, y **en qué archivo guardarlo** (la ruta sugerida, dentro de
`evidencias/`, para que el informe solo tenga que citarla).

---

## A5.15 — Control de acceso

- [ ] **#1 — Política de control de acceso documentada** (BRECHA, peso 3)
  **Dónde:** documental. **Acción:** busca en el repositorio de Gitea, en
  `README.md` y en cualquier wiki/documento entregado por "Dirección" una
  política de control de acceso firmada y con fecha de revisión. No existe
  ninguna en este laboratorio — esa ausencia **es** el hallazgo.
  **Guardar en:** `evidencias/A5.15/01_politica_acceso.txt` — anota dónde
  buscaste y que no encontraste evidencia (cita la fila #1 de `CONTROLES.md`).

- [ ] **#2 — Propietarios de activos identificados** (FUERTE, peso 2)
  **Dónde:** documental. **Acción:** transcribe la fila #2 de
  `CONTROLES.md` (en este ejercicio se asume evidenciada, como contraste
  del punto anterior).
  **Guardar en:** `evidencias/A5.15/02_propietarios_activos.txt`.

- [ ] **#3 — RBAC validado en servidor** (FUERTE, peso 3)
  **Dónde:** T2 (`nortia-kali`) o T1, con `curl`.
  ```bash
  curl -s -c cookies_jgarcia.txt -X POST http://portal:5000/login \
    -d "username=jgarcia&password=Nortia#2024" -L -o /dev/null -w "login: %{http_code}\n"
  curl -s -b cookies_jgarcia.txt -o /dev/null -w "GET /admin/usuarios/ -> %{http_code}\n" http://portal:5000/admin/usuarios/
  curl -s -b cookies_jgarcia.txt -o /dev/null -w "GET /finanzas/        -> %{http_code}\n" http://portal:5000/finanzas/
  curl -s -b cookies_jgarcia.txt -o /dev/null -w "GET /clientes/        -> %{http_code}\n" http://portal:5000/clientes/
  ```
  **Resultado esperado:** login 200/302, `/admin/usuarios/` y `/finanzas/`
  devuelven **403** (jgarcia es `comercial`), `/clientes/` devuelve 200.
  **Guardar en:** `evidencias/A5.15/03_rbac_bypass.txt` (pega la salida del
  comando).

- [ ] **#4 — Mínimo privilegio (sin privilegios residuales)** (BRECHA, peso 3)
  **Dónde:** T1 o T2, consulta SQL directa.
  ```bash
  docker exec -it nortia-db psql -U nortia_admin -d nortia \
    -c "SET search_path TO portal; SELECT username, rol, cargo, is_active_account FROM users WHERE username IN ('jrios','aherrera');"
  ```
  **Resultado esperado:** ambas cuentas con `is_active_account = t`, y el
  campo `cargo` describiendo explícitamente que son ex-empleados cuyos
  permisos nunca se revocaron.
  **Guardar en:** `evidencias/A5.15/04_privilegios_residuales.txt`.

---

## A9.2 — Gestión de accesos de usuario

- [ ] **#5 — Procedimiento formal de alta de usuarios** (FUERTE, peso 2)
  **Dónde:** navegador. **Acción:** entra a `http://127.0.0.1:5000/login`
  como `fguzman` / `Nortia#2024` (pide MFA — ver nota del ítem #8 para
  generar el código), ve a **Usuarios → Nuevo**, crea un usuario de prueba
  (ej. `auditor_test`, rol `operaciones`). Captura el mensaje con la clave
  temporal generada.
  **Verificación cruzada (T1):**
  ```bash
  docker exec -it nortia-db psql -U nortia_admin -d nortia \
    -c "SET search_path TO portal; SELECT accion, objeto, detalle, timestamp FROM audit_log WHERE objeto LIKE '%auditor_test%';"
  ```
  **Resultado esperado:** fila `USUARIO_ALTA` en `audit_log` con el mismo
  objeto y timestamp.
  **Guardar en:** `evidencias/A9.2/05_alta_usuario.txt` (pega la salida SQL
  y, si quieres, deja también una captura `05_alta_usuario.png` aparte).

- [ ] **#6 — Modificación de accesos con bitácora** (FUERTE, peso 2)
  **Dónde:** navegador. **Acción:** edita el rol de `auditor_test` (o
  cualquier otro) desde **Usuarios → Editar**.
  **Verificación cruzada (T1):**
  ```bash
  docker exec -it nortia-db psql -U nortia_admin -d nortia \
    -c "SET search_path TO portal; SELECT * FROM audit_log WHERE accion='USUARIO_CAMBIO_ROL' ORDER BY timestamp DESC LIMIT 5;"
  ```
  **Resultado esperado:** el cambio de rol queda registrado.
  **Guardar en:** `evidencias/A9.2/06_cambio_rol.txt`.

- [ ] **#7 — Procedimiento de baja/revocación** (BRECHA, peso 3)
  **Dónde:** T1, consulta SQL.
  ```bash
  docker exec -it nortia-db psql -U nortia_admin -d nortia \
    -c "SET search_path TO portal; SELECT username, cargo, is_active_account FROM users WHERE username='aherrera';"
  ```
  **Resultado esperado:** `is_active_account = t` aunque el campo `cargo`
  diga explícitamente "retirada hace 3 meses".
  **Guardar en:** `evidencias/A9.2/07_baja_no_revocada.txt`.

- [ ] **#8 — Rol diferenciado "administrador de seguridad" + MFA** (FUERTE, peso 3)
  **Dónde:** navegador + T2 (para generar el código TOTP).
  ```bash
  # en nortia-kali:
  apt install -y oathtool
  oathtool --totp -b <SECRETO_MFA_DE_FGUZMAN>   # imprime el código vigente por 30s
  ```
  (El secreto se obtiene con `docker compose logs portal | grep -A2 "\[seed\]"`
  en T1.) **Acción:** inicia sesión como `fguzman`, en la pantalla de MFA
  pega el código generado antes de que expire.
  **Resultado esperado:** acceso solo se concede tras el segundo factor;
  sin el código correcto, el login se detiene en `/mfa`.
  **Guardar en:** `evidencias/A9.2/08_mfa_login.txt` (describe el flujo:
  código generado, hora, resultado; si quieres, deja también una captura
  `08_mfa_login.png` aparte).

- [ ] **#9 — Revisión periódica de accesos (recertificación)** (BRECHA, peso 2)
  **Dónde:** documental. **Acción:** busca evidencia de una campaña de
  recertificación de accesos (actas, correos, tickets). No existe ninguna.
  **Guardar en:** `evidencias/A9.2/09_sin_recertificacion.txt` (nota de
  ausencia, citando que #4 y #7 son la consecuencia directa de no tenerla).

---

## A9.3 — Responsabilidades de los usuarios

- [ ] **#10 — Gestión de calidad de contraseñas comunicada** (FUERTE, peso 2)
  **Dónde:** reutiliza la evidencia del ítem #5. **Acción:** confirma que
  la clave temporal generada al crear `auditor_test` es aleatoria y de alta
  entropía (no una clave fija elegida a mano).
  **Guardar en:** `evidencias/A9.3/10_calidad_clave.txt` (referencia cruzada
  a `evidencias/A9.2/05_alta_usuario.txt`).

- [ ] **#11 — Perfiles de puesto con responsabilidades de seguridad** (BRECHA, peso 1)
  **Dónde:** documental. **Acción:** busca descripciones de cargo de RRHH
  que mencionen responsabilidades de seguridad de la información. No
  existen en este laboratorio.
  **Guardar en:** `evidencias/A9.3/11_perfiles_cargo.txt`.

- [ ] **#12 — Política de escritorio limpio** (BRECHA, peso 1)
  **Dónde:** documental/física. **Acción:** anota que no hay política
  firmada ni forma de verificarla en un laboratorio remoto — regístralo
  como "no evidenciable en este entorno, requeriría visita física".
  **Guardar en:** `evidencias/A9.3/12_escritorio_limpio.txt`.

---

## A9.4 — Control de acceso a sistemas y aplicaciones

- [ ] **#13 — RBAC en backend (consistencia entre módulos)** (FUERTE, peso 3)
  Reutiliza la evidencia de **#3**; es la misma prueba vista desde el
  ángulo de A9.4. **Guardar en:** `evidencias/A9.4/13_rbac_backend.txt`
  (referencia a `evidencias/A5.15/03_rbac_bypass.txt`).

- [ ] **#14 — Log-on seguro, portal principal** (FUERTE, peso 3)
  **Dónde:** T2.
  ```bash
  hydra -l jgarcia -P /usr/share/wordlists/rockyou.txt portal -s 5000 \
    http-post-form "/login:username=^USER^&password=^PASS^:F=incorrectos" -t 1 -V -W 2
  ```
  **Resultado esperado:** tras el 5º intento, el mensaje de error cambia de
  "incorrectos" a "bloqueada" — el ataque se corta solo. Revisa **T3**: debe
  aparecer una entrada `LOCKED` en `auth_portal.log`.
  **Guardar en:** `evidencias/A9.4/14_logon_portal.txt` (salida de Hydra) +
  captura de la línea `LOCKED` en los logs.

- [ ] **#15 — Log-on seguro, portal legacy** (BRECHA, peso 3)
  **Dónde:** T2.
  ```bash
  hydra -l soporte -P /usr/share/wordlists/rockyou.txt legacy -s 5001 \
    http-post-form "/:username=^USER^&password=^PASS^:F=incorrectos" -t 4 -V
  ```
  **Resultado esperado:** Hydra sigue probando sin ningún bloqueo (puede
  tardar; para una demo rápida usa una wordlist corta que incluya
  `soporte2024`). Revisa **T3**/`auth_legacy.log`: decenas de `FAILED`
  seguidas sin ningún `LOCKED`.
  **Guardar en:** `evidencias/A9.4/15_logon_legacy.txt`.

- [ ] **#16 — Gestión de calidad de contraseñas, portal** (FUERTE, peso 3)
  Reutiliza la evidencia de **#10**. **Guardar en:**
  `evidencias/A9.4/16_calidad_clave_portal.txt` (referencia cruzada).

- [ ] **#17 — Gestión de calidad de contraseñas, SSH/legacy** (BRECHA, peso 3)
  **Dónde:** T2.
  ```bash
  # MD5 del legacy:
  docker exec -it nortia-db psql -U nortia_admin -d nortia \
    -c "SET search_path TO legacy; SELECT username, password_md5 FROM usuarios_proveedores;"
  # pega el resultado como usuario:hash en hashes_legacy.txt, luego:
  john --format=Raw-MD5 --wordlist=/usr/share/wordlists/rockyou.txt hashes_legacy.txt
  john --show --format=Raw-MD5 hashes_legacy.txt

  # shadow del ssh-lab:
  docker cp nortia-ssh-lab:/opt/dumps/shadow_dump.txt .
  john --wordlist=/usr/share/wordlists/rockyou.txt shadow_dump.txt
  john --show shadow_dump.txt
  ```
  **Resultado esperado:** varias contraseñas caen rápido (coinciden con
  `ssh-lab/users.csv`).
  **Guardar en:** `evidencias/A9.4/17_john_legacy.txt` y
  `evidencias/A9.4/17_john_ssh.txt`.

- [ ] **#18 — Cuentas nominativas (sin cuentas compartidas)** (BRECHA, peso 2)
  **Dónde:** T1/T2.
  ```bash
  docker exec -it nortia-db psql -U nortia_admin -d nortia \
    -c "SET search_path TO legacy; SELECT username, nombre_proveedor FROM usuarios_proveedores WHERE username='soporte';"
  docker exec -it nortia-ssh-lab getent passwd soporte
  ```
  **Resultado esperado:** la cuenta `soporte` existe en ambos sistemas,
  descrita como compartida por el equipo de soporte del integrador — sin
  atribución a una persona física.
  **Guardar en:** `evidencias/A9.4/18_cuenta_compartida.txt`.

- [ ] **#19 — Acceso restringido al código fuente** (BRECHA, peso 2)
  **Dónde:** T2.
  ```bash
  curl -s -u gitea_admin:NortiaGiteaAdmin2024 \
    http://gitea:3000/api/v1/repos/nortia/portal-nortia/collaborators | grep -E "login|permission"
  git clone http://cjimenez:desarrollo123@gitea:3000/nortia/portal-nortia.git
  cat portal-nortia/config/legacy_db.conf
  ```
  **Resultado esperado:** `cjimenez` y `sgomez` con `"permission":"admin"`
  (no `"write"`), y la credencial `LEGACY_DB_PASSWORD=Integracion#2019` en
  texto plano dentro del repo.
  **Guardar en:** `evidencias/A9.4/19_gitea_permisos.txt` +
  `evidencias/A9.4/19_credencial_expuesta.txt` (copia del archivo).

- [ ] **#20 — IDOR en `/clientes/<id>`** (BRECHA, peso 3)
  **Dónde:** T2 (o navegador manual).
  ```bash
  curl -s -c cookies_jgarcia.txt -X POST http://portal:5000/login \
    -d "username=jgarcia&password=Nortia#2024" -L -o /dev/null
  for i in $(seq 1 12); do
    echo "=== cliente $i ==="
    curl -s -b cookies_jgarcia.txt http://portal:5000/clientes/$i | grep -oE "<h2>[^<]*</h2>"
  done
  ```
  **Resultado esperado:** `jgarcia` ve el detalle de los 12 clientes, no
  solo los de su propia cartera (debería ver ~3 en el listado `/clientes/`).
  **Guardar en:** `evidencias/A9.4/20_idor_clientes.txt`.

---

## 1. Consolidación final (para escribir el informe)

- [ ] Revisa que `evidencias/` tenga un archivo por cada uno de los 20
  ítems anteriores.
- [ ] Para cada uno, anota en tu informe: **Estado** (🟢/🔴), **Score**,
  **Amenaza MAGERIT** y **Medición** — cópialos directamente de
  `CONTROLES.md` (sección 2), y referencia el archivo de evidencia
  correspondiente.
- [ ] Usa la tabla de la sección 3 de `CONTROLES.md` (brecha → amenaza →
  riesgo residual) como punto de partida para tu propio análisis de
  riesgos cuantitativo (activo × amenaza × probabilidad × impacto).
- [ ] Calcula/verifica el score ponderado por dominio con los pesos de
  `CONTROLES.md` y confírmalo contra la tabla de la sección 1 de ese mismo
  archivo (A5.15=65%, A9.2=62%, A9.3=58%, A9.4=51%, Global=57%).
