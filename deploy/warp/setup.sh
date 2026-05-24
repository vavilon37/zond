#!/bin/bash
# Установка Cloudflare Warp (wgcf) на VPS
set -e

WGCF_VERSION="2.2.21"
WGCF_DIR="/opt/warp"
ARCH=$(uname -m)

case "$ARCH" in
  x86_64) WGCF_ARCH="amd64" ;;
  aarch64) WGCF_ARCH="arm64" ;;
  *) echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

mkdir -p "$WGCF_DIR"
cd "$WGCF_DIR"

if [ ! -f "wgcf" ]; then
  echo "==> Скачиваю wgcf ${WGCF_VERSION} (${WGCF_ARCH})..."
  curl -fsSL -o wgcf "https://github.com/ViRb3/wgcf/releases/download/v${WGCF_VERSION}/wgcf_${WGCF_VERSION}_linux_${WGCF_ARCH}"
  chmod +x wgcf
fi

if [ ! -f "wgcf-account.toml" ]; then
  echo "==> Регистрация Warp-аккаунта..."
  ./wgcf register --accept-tos
fi

if [ ! -f "wgcf-profile.conf" ]; then
  echo "==> Генерация Wireguard-профиля..."
  ./wgcf generate
fi

echo "==> Готово. Профиль в ${WGCF_DIR}/wgcf-profile.conf"
echo "==> Дальше запусти patch_warp.py чтобы добавить outbound в Marzban."
