#!/usr/bin/env bash
set -euo pipefail
rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/omarchy-spacex-sky" "$HOME/.local/bin/spacex-sky" \
       "${XDG_CACHE_HOME:-$HOME/.cache}/spacex-sky"
echo "Removed spacex-sky. (Remove any Waybar/Hyprland/systemd snippets you added by hand.)"
