#!/usr/bin/env bash
# Takibi Oracle sunucusuna kurar/günceller. Kullanım (Git Bash): TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... ./deploy/sunucuya_kur.sh
set -euo pipefail
SUNUCU="ubuntu@130.61.173.188"
ANAHTAR="$HOME/.ssh/oracle_asistan"
REPO="https://github.com/melik2706/ucus-fiyat-takip.git"
ssh -i "$ANAHTAR" "$SUNUCU" bash -s -- "$REPO" "${TELEGRAM_BOT_TOKEN:-}" "${TELEGRAM_CHAT_ID:-}" <<'REMOTE'
set -euo pipefail
REPO="$1"; TOKEN="$2"; CHAT="$3"
cd ~
[ -d ucus-fiyat-takip ] || git clone -q "$REPO" ucus-fiyat-takip
cd ucus-fiyat-takip && git pull --ff-only -q
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
mkdir -p ~/ucus-data
# İlk kurulumda depodaki son durumu (fiyat geçmişi) veri klasörüne taşı
[ -f ~/ucus-data/state.json ] || cp -n data/* ~/ucus-data/ 2>/dev/null || true
if [ -n "$TOKEN" ]; then
  umask 077
  printf 'TELEGRAM_BOT_TOKEN=%s\nTELEGRAM_CHAT_ID=%s\nTRACKER_DATA_DIR=/home/ubuntu/ucus-data\nTRACKER_JITTER=1\n' "$TOKEN" "$CHAT" > ~/ucus-data/.env
fi
sudo cp deploy/ucus-takip.service deploy/ucus-takip.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ucus-takip.timer
systemctl list-timers ucus-takip.timer --no-pager
REMOTE
