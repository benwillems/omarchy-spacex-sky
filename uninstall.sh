#!/usr/bin/env bash
# Removes the spacex-sky helper. Does not delete ~/.config/omarchy-spacex-sky.
set -euo pipefail

UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
systemctl --user disable --now spacex-sky-notify.timer 2>/dev/null || true
rm -f "$UNIT_DIR/spacex-sky-notify.service" "$UNIT_DIR/spacex-sky-notify.timer"
systemctl --user daemon-reload 2>/dev/null || true

rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/omarchy-spacex-sky" "$HOME/.local/bin/spacex-sky" \
       "${XDG_CACHE_HOME:-$HOME/.cache}/spacex-sky"

echo "Removed the spacex-sky helper."
echo "Remove the bar widget with: omarchy plugin remove bjw.spacex-sky"
echo "Favorites at ~/.config/omarchy-spacex-sky/ were left in place."
