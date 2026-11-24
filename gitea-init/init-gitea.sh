#!/bin/bash
# Aprovisiona Gitea para Nortia Distribuciones S.A.S.:
#   - usuario admin + 2 desarrolladores (cjimenez, sgomez)
#   - organizacion "nortia" y repositorio "portal-nortia"
#   - IMPORTANTE (brecha deliberada #19, A9.4.5): los dos desarrolladores
#     quedan como colaboradores con permiso "admin" sobre el repo, en vez de
#     "write". Todo el equipo de TI puede administrar el repositorio,
#     incluyendo ramas protegidas y ajustes de acceso, sin separacion de
#     ambientes dev/test/produccion.
#   - push del codigo fuente del portal, incluyendo un archivo de
#     configuracion heredado con una credencial de servicio "quemada" en el
#     repositorio (hallazgo clasico de auditoria de codigo fuente).
#
# Requiere el socket de Docker montado para poder ejecutar `gitea admin`
# dentro del contenedor oficial de Gitea (no se puede crear el primer admin
# solo por API cuando INSTALL_LOCK esta activo).

set -uo pipefail

GITEA_CONTAINER="${GITEA_CONTAINER:-nortia-gitea}"
GITEA_URL="http://gitea:3000"
ADMIN_USER="gitea_admin"
ADMIN_PASS="NortiaGiteaAdmin2024"
ADMIN_EMAIL="admin@nortia.co"

DEV1_USER="cjimenez"; DEV1_PASS="desarrollo123"; DEV1_EMAIL="cjimenez@nortia.co"
DEV2_USER="sgomez";   DEV2_PASS="sebas2023";      DEV2_EMAIL="sgomez@nortia.co"

ORG="nortia"
REPO="portal-nortia"

echo "[gitea-init] Esperando a que Gitea responda..."
for i in $(seq 1 60); do
  if curl -fsS "${GITEA_URL}/api/healthz" >/dev/null 2>&1; then
    echo "[gitea-init] Gitea disponible."
    break
  fi
  sleep 3
done

crear_usuario() {
  local user="$1" pass="$2" email="$3" admin_flag="$4"
  echo "[gitea-init] Creando usuario ${user}..."
  docker exec -u git "${GITEA_CONTAINER}" gitea admin user create \
    --username "${user}" --password "${pass}" --email "${email}" \
    ${admin_flag} --must-change-password=false \
    || echo "[gitea-init] (${user} probablemente ya existia, se continua)"
}

crear_usuario "${ADMIN_USER}" "${ADMIN_PASS}" "${ADMIN_EMAIL}" "--admin"
crear_usuario "${DEV1_USER}" "${DEV1_PASS}" "${DEV1_EMAIL}" ""
crear_usuario "${DEV2_USER}" "${DEV2_PASS}" "${DEV2_EMAIL}" ""

AUTH="${ADMIN_USER}:${ADMIN_PASS}"

echo "[gitea-init] Creando organizacion ${ORG}..."
curl -fsS -u "${AUTH}" -H "Content-Type: application/json" \
  -X POST "${GITEA_URL}/api/v1/orgs" \
  -d "{\"username\":\"${ORG}\",\"visibility\":\"private\"}" >/dev/null \
  || echo "[gitea-init] (org probablemente ya existia)"

echo "[gitea-init] Creando repositorio ${ORG}/${REPO}..."
curl -fsS -u "${AUTH}" -H "Content-Type: application/json" \
  -X POST "${GITEA_URL}/api/v1/orgs/${ORG}/repos" \
  -d "{\"name\":\"${REPO}\",\"private\":true,\"auto_init\":true,\"default_branch\":\"main\"}" >/dev/null \
  || echo "[gitea-init] (repo probablemente ya existia)"

for dev in "${DEV1_USER}" "${DEV2_USER}"; do
  echo "[gitea-init] Agregando a ${dev} como colaborador con permiso 'admin' (brecha #19 deliberada)..."
  curl -fsS -u "${AUTH}" -H "Content-Type: application/json" \
    -X PUT "${GITEA_URL}/api/v1/repos/${ORG}/${REPO}/collaborators/${dev}" \
    -d "{\"permission\":\"admin\"}" >/dev/null \
    || echo "[gitea-init] (no se pudo agregar a ${dev}, revisar manualmente)"
done

echo "[gitea-init] Preparando contenido con el codigo fuente del portal..."
WORKDIR=$(mktemp -d)
cd "${WORKDIR}" || exit 1
git config --global user.email "ci@nortia.co"
git config --global user.name "Nortia CI"
git config --global --add safe.directory "${WORKDIR}"

if git clone "http://${ADMIN_USER}:${ADMIN_PASS}@gitea:3000/${ORG}/${REPO}.git" repo 2>/tmp/clone.log; then
  cd repo || exit 1
  cp -r /src/portal-nortia/. ./portal-nortia/ 2>/dev/null || mkdir -p portal-nortia && cp -r /src/portal-nortia/. ./portal-nortia/

  mkdir -p config
  cat > config/legacy_db.conf <<'EOF'
# Configuracion heredada de la integracion con el portal legacy (fusion 2020).
# Pendiente de migrar a un gestor de secretos; nunca rotada desde entonces.
# --> Hallazgo de auditoria: credencial de servicio "quemada" en el repositorio (A9.4.5).
LEGACY_DB_HOST=legacy-db.nortia.local
LEGACY_DB_USER=svc_integracion
LEGACY_DB_PASSWORD=Integracion#2019
EOF

  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "Importacion inicial del codigo del portal (migracion post-fusion)" >/dev/null
    git push -u origin HEAD:main 2>/tmp/push.log || git push -u origin HEAD:master 2>>/tmp/push.log \
      || echo "[gitea-init] No se pudo hacer push automatico, revisar /tmp/push.log dentro del contenedor"
  else
    echo "[gitea-init] Repositorio ya tenia contenido, no se hace push de nuevo."
  fi
else
  echo "[gitea-init] No se pudo clonar el repo, revisar /tmp/clone.log"
fi

cat <<SUMMARY

================= GITEA APROVISIONADO =================
URL:            http://127.0.0.1:3000
Admin:          ${ADMIN_USER} / ${ADMIN_PASS}
Dev 1:          ${DEV1_USER} / ${DEV1_PASS}  (colaborador 'admin' sobre el repo - brecha #19)
Dev 2:          ${DEV2_USER} / ${DEV2_PASS}  (colaborador 'admin' sobre el repo - brecha #19)
Organizacion:   ${ORG}
Repositorio:    ${REPO}
=========================================================
SUMMARY
