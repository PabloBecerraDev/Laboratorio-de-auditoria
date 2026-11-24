# CONTROLES.md — Guion de auditoría Anexo 9 (Control de Accesos)
## Nortia Distribuciones S.A.S. — laboratorio académico

> ⚠️ Laboratorio deliberadamente vulnerable, atado a `127.0.0.1`, solo para uso
> educativo. Ver `README.md` para cómo levantarlo.

## 0. Cómo leer este documento

Este archivo es el guion que el grupo usa para auditar el laboratorio. Para
cada subcontrol del Anexo 9 se indica:

- **Peso**: 1 = control de apoyo/organizativo, 2 = control relevante, 3 =
  control crítico (su falla habilita directamente un acceso indebido).
- **Estado**: 🟢 FUERTE o 🔴 BRECHA.
- **Score** (0–100): nivel de cumplimiento observado para ese subcontrol.
- **Amenaza MAGERIT**: la amenaza del catálogo que la brecha habilita o
  facilita — es el insumo para que ustedes encadenen brecha → amenaza →
  riesgo residual en su propio análisis de riesgos (sección 5 de su informe).
- **Medición (Anexo 9)**: la métrica del anexo que evalúa ese punto.
- **Herramienta de verificación**: con qué lo comprobarían en la auditoría.

### Nota de contexto: por qué hay una "contradicción" en A5.15

Nortia tiene **bcrypt+sal, bloqueo por intentos, MFA para el administrador de
seguridad y RBAC validado en servidor** (controles técnicamente maduros) pero
**no tiene una política de control de acceso documentada y aprobada por
Dirección** (control #1, BRECHA). Esto no es un error de diseño del
laboratorio: es el patrón más común en PYMES colombianas después de una
fusión o un crecimiento acelerado — **el área de TI resuelve bien el "cómo"
técnico, pero el gobierno corporativo de la seguridad (el "quién decide, qué
se documenta, quién lo revisa") nunca se formalizó**. Es exactamente el tipo
de hallazgo que un auditor de Anexo 9 debe saber nombrar: controles técnicos
fuertes no sustituyen un marco de gobierno documentado, y una auditoría
rigurosa debe exigir ambos.

---

## 1. Resumen de cumplimiento por dominio

| Dominio | Descripción | Score ponderado |
|---|---|---|
| **A5.15** | Control de acceso (política, propietarios, RBAC, mínimo privilegio) | **65%** |
| **A9.2** | Gestión de accesos de usuario (alta/mod/baja, privilegios elevados) | **62%** |
| **A9.3** | Responsabilidades de los usuarios (contraseñas, perfiles, escritorio limpio) | **58%** |
| **A9.4** | Control de acceso a sistemas y aplicaciones (log-on, calidad de clave, código fuente) | **51%** |
| **GLOBAL** | Promedio ponderado de los 20 subcontroles evaluados | **57%** |

A9.4 es el dominio más débil — coherente con que ahí vive la deuda técnica
heredada del portal legacy, el laboratorio SSH y el repositorio de código.
A5.15 es el más fuerte porque el RBAC del portal principal está bien
implementado, aunque sin respaldo documental.

---

## 2. Tabla detallada por subcontrol

### A5.15 — Control de acceso

| # | Subcontrol | Alcance | Peso | Estado | Score | Amenaza MAGERIT | Medición (Anexo 9) | Herramienta |
|---|---|---|---|---|---|---|---|---|
| 1 | Política de control de acceso documentada, aprobada y revisada | Toda la empresa | 3 | 🔴 BRECHA | 30 | **A.6** Abuso de privilegios de acceso (cada área interpreta las reglas a su manera, sin criterio único) | % de sistemas con política de acceso formalmente aprobada y revisada | Revisión documental / entrevista a Dirección y Seguridad |
| 2 | Propietarios de activos identificados, con aceptación formal y revisión basada en riesgo | Portal principal | 2 | 🟢 FUERTE | 90 | — (control mitigante) | % de sistemas con propietario identificado y responsabilidades aceptadas | Revisión documental (matriz de propietarios + actas) |
| 3 | Modelo RBAC implementado y **validado en servidor** (no solo oculto en el frontend) | Portal principal | 3 | 🟢 FUERTE | 95 | — (control mitigante) | % de aplicaciones con reglas de control de acceso basadas en roles | ZAP/Burp (intento de bypass manipulando rol/endpoint) |
| 4 | Principio de mínimo privilegio (sin privilegios residuales) | Portal legacy + SSH | 3 | 🔴 BRECHA | 40 | **A.6** Abuso de privilegios de acceso / **A.11** Acceso no autorizado (cuentas de ex-empleados conservan permisos: `aherrera`, `jrios`) | % de cuentas activas con permisos acordes al cargo vigente | Consulta SQL directa a `portal.users` + cruce con nómina/RRHH |

### A9.2 — Gestión de accesos de usuario

| # | Subcontrol | Alcance | Peso | Estado | Score | Amenaza MAGERIT | Medición (Anexo 9) | Herramienta |
|---|---|---|---|---|---|---|---|---|
| 5 | Procedimiento formal de alta de usuarios | Portal principal | 2 | 🟢 FUERTE | 85 | — (control mitigante) | Tiempo medio solicitud→alta; # de altas/mes | Revisión del módulo "Administración de usuarios" + `audit_log` |
| 6 | Procedimiento de modificación de accesos, con bitácora | Portal principal | 2 | 🟢 FUERTE | 85 | — (control mitigante) | # de cambios de rol registrados vs. observados | Consulta a `portal.audit_log` (acción `USUARIO_CAMBIO_ROL`) |
| 7 | Procedimiento de baja/revocación de accesos | Toda la empresa | 3 | 🔴 BRECHA | 35 | **A.11** Acceso no autorizado (cuenta `aherrera`, ex-empleada, sigue activa 3 meses después de su salida) | % de bajas de personal con revocación de acceso en ≤ 24h | Cruce de fecha de salida (RRHH) vs. `is_active_account` en `portal.users` |
| 8 | Rol diferenciado "administrador de seguridad" + control de privilegios elevados + MFA | Portal principal | 3 | 🟢 FUERTE | 90 | — (control mitigante) | % de cuentas con privilegios elevados que usan MFA | Verificación manual del flujo de login de `fguzman` |
| 9 | Revisión periódica de accesos (recertificación) | Toda la empresa | 2 | 🔴 BRECHA | 15 | **A.6** Abuso de privilegios de acceso (privilegios desactualizados nunca se detectan porque nadie los revisa) | Existencia de campañas de recertificación y su periodicidad | Entrevista a Seguridad/TI; ausencia de evidencia documental |

### A9.3 — Responsabilidades de los usuarios

| # | Subcontrol | Alcance | Peso | Estado | Score | Amenaza MAGERIT | Medición (Anexo 9) | Herramienta |
|---|---|---|---|---|---|---|---|---|
| 10 | Gestión de contraseñas comunicada a los usuarios (complejidad, expiración) | Portal principal | 2 | 🟢 FUERTE | 80 | — (control mitigante) | % de usuarios con política de clave comunicada y aplicada | Observación del formulario de login/cambio de clave |
| 11 | Perfiles de puesto con responsabilidades de seguridad documentadas | RRHH | 1 | 🔴 BRECHA | 45 | **A.30** Ingeniería social / **E.2** Errores del personal (falta de conciencia de su rol en la seguridad) | % de descripciones de puesto con responsabilidades de SI, documentadas y aceptadas | Revisión documental de perfiles de cargo en RRHH |
| 12 | Política de escritorio limpio | Oficinas | 1 | 🔴 BRECHA | 25 | **A.25** Robo / **A.19** Divulgación de información (documentos o sesiones expuestas en el puesto de trabajo) | Existencia de política firmada + verificación en sitio | Checklist de recorrido físico / entrevista |

### A9.4 — Control de acceso a sistemas y aplicaciones

| # | Subcontrol | Alcance | Peso | Estado | Score | Amenaza MAGERIT | Medición (Anexo 9) | Herramienta |
|---|---|---|---|---|---|---|---|---|
| 13 | Restricción de acceso según política (RBAC en backend) | Portal principal | 3 | 🟢 FUERTE | 90 | — (control mitigante) | % de módulos con control de acceso aplicado consistentemente en servidor | ZAP/Burp (intento de acceso directo a rutas sin el rol requerido) |
| 14 | Procedimiento de log-on seguro (hash moderno+sal, bloqueo por intentos, MFA admin) | **Portal principal** | 3 | 🟢 FUERTE | 90 | — (control mitigante) | Estadísticas de intentos bloqueados / tasa de éxito de fuerza bruta | Hydra contra `:5000/login` (debe fallar por el bloqueo) |
| 15 | Procedimiento de log-on seguro | **Portal legacy proveedores** | 3 | 🔴 BRECHA | 15 | **A.5** Suplantación de identidad / **A.11** Acceso no autorizado (sin bloqueo de intentos, sin MFA) | Estadísticas de intentos bloqueados — en legacy: 0 bloqueos posibles | Hydra (`http-post-form`) contra `:5001/`; Nikto contra la config del servicio |
| 16 | Gestión de calidad de contraseñas | Portal principal | 3 | 🟢 FUERTE | 85 | — (control mitigante) | % de contraseñas que cumplen la política de complejidad | Intento de registro/cambio de clave con valores débiles |
| 17 | Gestión de calidad de contraseñas | **Cuentas SSH / legacy** | 3 | 🔴 BRECHA | 20 | **A.5** Suplantación de identidad (adivinación de contraseñas por diccionario) | % de cuentas con contraseña débil o reutilizada | John the Ripper sobre `/opt/dumps/shadow_dump.txt`; Hydra contra `:2222` |
| 18 | Cuentas nominativas (sin cuentas genéricas compartidas) | Legacy + SSH | 2 | 🔴 BRECHA | 30 | **A.13** Repudio (no se puede atribuir una acción a una persona) / **A.5** Suplantación de identidad | % de cuentas activas asociadas a una sola persona identificable | Revisión de `legacy.usuarios_proveedores` y `/etc/passwd` del `ssh-lab` (cuenta `soporte`) |
| 19 | Acceso restringido al código fuente | Gitea / repositorio | 2 | 🔴 BRECHA | 30 | **A.11** Acceso no autorizado / **A.15** Modificación deliberada de la información (código) | % de repositorios con control de acceso granular por rol/ambiente | Revisión de permisos de colaboradores en Gitea (`cjimenez`/`sgomez` con permiso `admin` en vez de `write`); inspección del repo (credencial en `config/legacy_db.conf`) |
| 20 | Control de acceso **a nivel de objeto/registro** (granularidad de campos específicos, principio citado en A5.15) | **Módulo Clientes, portal principal** | 3 | 🔴 BRECHA | 35 | **A.11** Acceso no autorizado / **A.19** Divulgación de información (IDOR/BOLA: un comercial ve clientes fuera de su cartera) | % de módulos con validación de propiedad del registro, no solo del rol | ZAP/Burp: fuzzing de IDs secuenciales en `/clientes/<id>` autenticado como rol `comercial` |

---

## 3. Relación brecha → amenaza → riesgo residual (insumo para su análisis de riesgos)

Esta tabla no reemplaza el análisis de riesgos cuantitativo de su informe
(activo × amenaza × probabilidad × impacto, como en el ejemplo de la
profesora); es el puente entre lo que encontraron en la auditoría de
controles y lo que deben cuantificar después:

| Brecha | Activo más expuesto | Amenaza MAGERIT | Por qué importa |
|---|---|---|---|
| #15 Log-on inseguro (legacy) | Credenciales de proveedores, cupos de crédito | A.5 Suplantación de identidad | Sin bloqueo de intentos, una cuenta se compromete por fuerza bruta en minutos |
| #17 Contraseñas débiles (SSH) | Acceso a los servidores de Nortia | A.5 Suplantación de identidad | Las cuentas de empleados (incluida la de un ex-practicante, #4) son la puerta de entrada a todo el host |
| #18 Cuentas compartidas | Trazabilidad de incidentes | A.13 Repudio | Si "soporte" hace algo indebido, no hay forma de saber qué persona física lo hizo |
| #19 Código sin control granular | Propiedad intelectual, credenciales en el repo | A.11 / A.15 | Cualquier developer puede alterar el historial o exponer la credencial `Integracion#2019` |
| #20 IDOR en Clientes | Datos comerciales de clientes de la competencia | A.11 / A.19 | Un comercial despedido en malos términos podría, antes de su baja (ver #7), exportar toda la cartera de otros comerciales |
| #7 Bajas no revocadas | Acceso residual general | A.11 | Combinada con #4 y #20, una cuenta de ex-empleado activa es el escenario de mayor riesgo compuesto del laboratorio |

---

## 4. Herramientas sugeridas por objetivo

| Herramienta | Para qué se usa aquí |
|---|---|
| **Nmap** | Enumerar servicios/puertos expuestos en 127.0.0.1 (5000, 5001, 2222, 3000, 5432) y confirmar que nada quedó accesible fuera de loopback |
| **Hydra** | Fuerza bruta contra el login del portal legacy (`:5001`, sin bloqueo) y contra SSH (`:2222`) |
| **John the Ripper** | Crackeo de los hashes MD5 de `legacy.usuarios_proveedores` (volcado vía SQL) y de `/opt/dumps/shadow_dump.txt` en `ssh-lab` |
| **ZAP / Burp Suite** | Bypass de RBAC (comparar portal principal vs. legacy), fuzzing de IDs en `/clientes/<id>` (brecha #20) |
| **Nikto** | Configuración débil del servidor del portal legacy (cabeceras, métodos HTTP, información filtrada) |
| **Revisión documental / entrevistas** | Todas las brechas organizativas: #1, #7, #9, #11, #12 |
