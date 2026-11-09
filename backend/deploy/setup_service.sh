#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_NAME="followup-agent.service"

sudo cp "$SCRIPT_DIR/$UNIT_NAME" "/etc/systemd/system/$UNIT_NAME"
sudo systemctl daemon-reload
sudo systemctl enable "$UNIT_NAME"
sudo systemctl restart "$UNIT_NAME"
sudo systemctl status "$UNIT_NAME" --no-pager
