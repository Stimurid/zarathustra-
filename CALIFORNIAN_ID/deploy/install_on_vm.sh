#!/usr/bin/env bash
# Установка / обновление tinkuy на VM.
# Запускается как sudo с /tmp/tinkuy-deploy.tar.gz на месте.
set -euo pipefail

INSTANCE="${INSTANCE:-tinkuy}"
PORT="${PORT:-8085}"
DOMAIN="${DOMAIN:-tinkuy.mindkampf.ru}"

APP_ROOT="/opt/${INSTANCE}"
APP_DIR="${APP_ROOT}/app"
ETC_DIR="/etc/${INSTANCE}"
SRV_DIR="/srv/${INSTANCE}"
ENV_FILE="${ETC_DIR}/${INSTANCE}.env"
SERVICE_UNIT="/etc/systemd/system/${INSTANCE}-web.service"
TARBALL="/tmp/${INSTANCE}-deploy.tar.gz"

echo "==> User + dirs"
useradd --system --home "${APP_ROOT}" --shell /usr/sbin/nologin "${INSTANCE}" 2>/dev/null || true
mkdir -p "${APP_DIR}" "${ETC_DIR}" "${SRV_DIR}/runs"
chown -R "${INSTANCE}:${INSTANCE}" "${APP_ROOT}" "${SRV_DIR}"

echo "==> Extract code"
if [ ! -s "${TARBALL}" ]; then
    echo "ERR: ${TARBALL} not found or empty" >&2
    exit 1
fi
# Wipe app dir (keep .venv to save reinstall)
find "${APP_DIR}" -mindepth 1 -maxdepth 1 -not -name ".venv" -exec rm -rf {} +
tar -xzf "${TARBALL}" -C "${APP_DIR}"
chown -R "${INSTANCE}:${INSTANCE}" "${APP_DIR}"

echo "==> Venv"
if [ ! -x "${APP_DIR}/.venv/bin/python" ]; then
    sudo -u "${INSTANCE}" python3 -m venv "${APP_DIR}/.venv"
fi
sudo -u "${INSTANCE}" "${APP_DIR}/.venv/bin/pip" install --upgrade pip wheel setuptools >/dev/null

echo "==> Install package"
sudo -u "${INSTANCE}" "${APP_DIR}/.venv/bin/pip" install "pyyaml>=6.0"
# Editable install of the CALIFORNIAN_ID package
sudo -u "${INSTANCE}" "${APP_DIR}/.venv/bin/pip" install -e "${APP_DIR}/CALIFORNIAN_ID"

echo "==> Env file"
if [ ! -f "${ENV_FILE}" ]; then
    install -m 600 -o "${INSTANCE}" -g "${INSTANCE}" \
        "${APP_DIR}/CALIFORNIAN_ID/deploy/${INSTANCE}.env.template" "${ENV_FILE}"
    echo "    ${ENV_FILE} создан (mock provider по умолчанию)"
else
    echo "    ${ENV_FILE} уже есть — не трогаю"
fi

echo "==> systemd unit"
install -m 644 -o root -g root \
    "${APP_DIR}/CALIFORNIAN_ID/deploy/${INSTANCE}.service" "${SERVICE_UNIT}"
systemctl daemon-reload
systemctl enable "${INSTANCE}-web.service"
# Force restart even if service is already active (unit contents may have changed).
systemctl restart "${INSTANCE}-web.service"
sleep 2
systemctl status --no-pager -l "${INSTANCE}-web.service" | head -18

echo "==> Health"
sleep 1
curl -sSf "http://127.0.0.1:${PORT}/" -o /dev/null && echo "    OK: http://127.0.0.1:${PORT}/ отвечает"

echo "==> Done. Осталось: Caddy-блок и reload."
