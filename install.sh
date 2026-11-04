#!/usr/bin/env bash
# Installs the spacex-sky helper for the current user only (no sudo).
# The Omarchy bar widget is installed with:
#   omarchy plugin add https://github.com/benwillems/omarchy-spacex-sky.git --enable
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/omarchy-spacex-sky"
BIN="$HOME/.local/bin"
PLUGIN_DEST="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/bjw.spacex-sky"

command -v python3 >/dev/null || { echo "python3 is required (omarchy pkg add python)"; exit 1; }

echo "→ Copying app to $DEST"
mkdir -p "$DEST" "$BIN"
rm -rf "$DEST/spacex_sky"
cp -r "$SRC/spacex_sky" "$SRC/requirements.txt" "$DEST/"

echo "→ Creating virtualenv and installing Skyfield"
[ -x "$DEST/venv/bin/python" ] || python3 -m venv "$DEST/venv"
"$DEST/venv/bin/pip" install --quiet --upgrade pip
"$DEST/venv/bin/pip" install --quiet -r "$DEST/requirements.txt"

echo "→ Writing $BIN/spacex-sky"
cat > "$BIN/spacex-sky" <<WRAP
#!/usr/bin/env bash
cd "$DEST" && exec "$DEST/venv/bin/python" -m spacex_sky "\$@"
WRAP
chmod +x "$BIN/spacex-sky"

echo "→ Warming caches (downloads ~17 MB planet ephemeris once)"
"$BIN/spacex-sky" launches --limit 1 >/dev/null || echo "  (launch data fetch failed; it will retry later)"
"$BIN/spacex-sky" trains --top 1 >/dev/null || echo "  (Starlink data fetch failed; it will retry later)"

case ":$PATH:" in *":$BIN:"*) ;; *) echo "NOTE: add $BIN to your PATH";; esac

src_real=$(readlink -f "$SRC")
plugin_real=$(readlink -f "$PLUGIN_DEST" 2>/dev/null || true)
if [ "$src_real" != "$plugin_real" ]; then
  echo "→ Bar widget: omarchy plugin add https://github.com/benwillems/omarchy-spacex-sky.git --enable"
fi

echo "✓ Helper installed. Try:  spacex-sky launches   |   spacex-sky trains"
echo "  Optional desktop alerts (not enabled automatically):"
echo "    mkdir -p ~/.config/systemd/user"
echo "    cp \"$SRC/systemd/spacex-sky-notify.\"{service,timer} ~/.config/systemd/user/"
echo "    systemctl --user daemon-reload"
echo "    systemctl --user enable --now spacex-sky-notify.timer"
