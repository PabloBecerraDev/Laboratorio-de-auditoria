# Laboratorio de auditoria — Nortia Distribuciones S.A.S.

> ⚠️ **ENTORNO DELIBERADAMENTE VULNERABLE, SOLO PARA USO LOCAL Y EDUCATIVO.**
> Todos los servicios quedan atados a `127.0.0.1` (ver `docker-compose.yml`).
> No lo despliegues en una red compartida, en la nube, ni con datos reales.
> Los datos de empleados, clientes y nomina son 100% ficticios.

Este repositorio es el laboratorio práctico del curso de auditoría de seguridad
(ISO 27001/27002), construido alrededor del **Anexo 9 — Control de Accesos**.
Simula la infraestructura de **Nortia Distribuciones S.A.S.**, una empresa
colombiana ficticia de distribución mayorista, con un reparto deliberado de
controles **fuertes** y **con brecha** para que el cumplimiento quede parcial
(~57%, ver [`CONTROLES.md`](./CONTROLES.md)).

## Que incluye

| Servicio | Descripcion | Puerto (127.0.0.1) |
|---|---|---|
| `portal` | Intranet principal: Clientes, Nomina, Finanzas, Administracion de usuarios, Solicitudes de acceso. RBAC validado en servidor, bcrypt+sal, bloqueo por intentos, MFA para el administrador de seguridad. | `5000` |
| `legacy` | Portal de proveedores heredado de una fusion. Hash MD5 sin sal, sin bloqueo de intentos, sin MFA, cuenta generica compartida. | `5001` |
| `ssh-lab` | Contenedor Linux con ~20 cuentas de empleados (varias con contrasenas debiles o reutilizadas) para practicar Hydra/John. | `2222` |
| `gitea` | Repositorio de codigo con el portal principal. Los dos "desarrolladores" quedan como colaboradores con permiso `admin` en vez de `write` (brecha de acceso al codigo fuente). | `3000` |
| `db` | Postgres compartido, esquemas `portal` y `legacy` separados. | `5432` |

Los logs (autenticacion del portal, autenticacion del legacy, firewall
simulado) quedan en `./logs/` en el host, montados como volumen.

## Requisitos

- Docker y Docker Compose v2.
- Linux/macOS/WSL2 recomendado. En Windows nativo, el bind mount del socket
  de Docker para `gitea-init` requiere Docker Desktop con integracion WSL2
  o el backend de Linux containers activo.

## Como levantar el laboratorio

```bash
cp .env.example .env
docker compose up -d --build
```

La primera vez, espera ~30-60 segundos a que Postgres quede listo, el portal
se siembre y Gitea termine su aprovisionamiento (`gitea-init` corre una sola
vez y termina; revisa su log con `docker compose logs gitea-init`).

Para ver las credenciales generadas (password de demo del portal, secreto MFA
del administrador de seguridad):

```bash
docker compose logs portal | grep -A2 "\[seed\]"
```

## Acceso

- **Portal principal:** http://127.0.0.1:5000 — usuario, por ejemplo
  `fguzman` (administrador de seguridad, pide MFA) o `jgarcia` (comercial).
  Password de demo: `Nortia#2024` (ver `portal/seed.py`).
- **Portal legacy de proveedores:** http://127.0.0.1:5001 — ver usuarios en
  `legacy-portal/app.py` (`USUARIOS_SEMILLA`), incluida la cuenta compartida
  `soporte` / `soporte2024`.
- **SSH lab:** `ssh -p 2222 <usuario>@127.0.0.1` — ver `ssh-lab/users.csv`.
- **Gitea:** http://127.0.0.1:3000 — `gitea_admin` / `NortiaGiteaAdmin2024`, o
  los desarrolladores `cjimenez` / `desarrollo123` y `sgomez` / `sebas2023`.

## Para el ejercicio de auditoria

`CONTROLES.md` es el guion: mapea cada subcontrol del Anexo 9 a como quedo
implementado (fuerte/brecha), su score ponderado, la amenaza MAGERIT asociada
y la herramienta con la que se verificaria (John, Hydra, Nmap, ZAP/Burp,
Nikto, revision documental). Usen esa tabla como checklist de la auditoria.

## Reiniciar / limpiar el laboratorio

```bash
docker compose down -v   # borra tambien los volumenes (DB y Gitea)
rm -rf logs/*
```

## Estructura del repositorio

```
.
├── docker-compose.yml
├── db/init.sql                 # crea los esquemas portal/legacy
├── portal/                     # intranet principal (Flask + Postgres)
├── legacy-portal/               # portal de proveedores (legacy, debil a proposito)
├── ssh-lab/                     # contenedor Linux con cuentas de empleados
├── gitea-init/                  # aprovisiona Gitea (usuarios, org, repo, permisos)
├── logs/                        # logs generados en runtime (montado)
└── CONTROLES.md                 # guion de auditoria Anexo 9
```
