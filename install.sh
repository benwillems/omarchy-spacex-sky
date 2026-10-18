#!/usr/bin/env bash
# Installs spacex-sky for the current user only (no sudo, nothing system-wide).
#   app:     ~/.local/share/omarchy-spacex-sky  (code + its own Python venv)
#   command: ~/.local/bin/spacex-sky
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/omarchy-spacex-sky"
BIN="$HOME/.local/bin"

command -v python3 >/dev/null || { echo "python3 is required (sudo pacman -S python)"; exit 1; }

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
echo "✓ Installed. Try:  spacex-sky launches   |   spacex-sky trains"
echo "  Waybar / Hyprland / notification snippets: see README.md"
