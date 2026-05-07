#!/usr/bin/env bash
set -euo pipefail

APP_NAME="botvpnredirect"
INSTALL_DIR="/opt/${APP_NAME}"
SERVICE_NAME="${APP_NAME}.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/7] Installing system packages"
apt update
apt install -y python3 python3-pip python3-venv git

echo "[2/7] Preparing application directory: ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"

echo "[3/7] Copying project files"
cp "${SCRIPT_DIR}"/multi_bot_redirect.py "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}"/app_*.py "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}"/requirements.txt "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}"/botvpnredirect.service "${INSTALL_DIR}/"

touch "${INSTALL_DIR}/.env"
[ -f "${INSTALL_DIR}/bot_tokens.json" ] || printf '[]\n' > "${INSTALL_DIR}/bot_tokens.json"
[ -f "${INSTALL_DIR}/channels.json" ] || printf '[]\n' > "${INSTALL_DIR}/channels.json"
[ -f "${INSTALL_DIR}/button_stats.json" ] || printf '{"bots": {}}\n' > "${INSTALL_DIR}/button_stats.json"

echo "[4/7] Creating virtual environment"
python3 -m venv "${INSTALL_DIR}/.venv"

echo "[5/7] Installing Python dependencies"
"${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

echo "[6/7] Installing systemd service"
cp "${INSTALL_DIR}/botvpnredirect.service" "${SERVICE_PATH}"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

echo "[7/7] Restarting service"
systemctl restart "${SERVICE_NAME}"

echo
echo "Installation completed."
echo "Service status:"
systemctl --no-pager --full status "${SERVICE_NAME}" || true
echo
echo "Useful commands:"
echo "  journalctl -u ${SERVICE_NAME} -f"
echo "  systemctl restart ${SERVICE_NAME}"
