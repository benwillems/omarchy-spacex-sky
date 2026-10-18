# omarchy-spacex-sky 🚀✨

A small Omarchy (Arch + Hyprland + Waybar) helper for watching SpaceX from your
backyard with the kids:

- **`spacex-sky launches`**: upcoming SpaceX launches in Eastern time, with a big
  🌴 **FLORIDA** marker for Cape Canaveral / Kennedy pads (vs. California and Texas),
  which way to look, and whether it's a night, twilight or daytime launch.
- **`spacex-sky trains`**: ranked, visible **Starlink "train"** passes for recently
  launched groups: when, which direction to face, how high, how long, plus a
  kid-friendly line to read out loud.
- **`spacex-sky waybar`**: a Waybar module showing `🚀 FL 1d 5h` (next Florida launch
  countdown), with `★ 7:16pm` in front when a train passes tonight.
- **`spacex-sky notify`**: a desktop notification 15 minutes before a pass (and,
  optionally, a Florida launch), run from a systemd *user* timer.

Defaults to Jacksonville, FL (30.13 N, 81.53 W) in America/New_York.

## Install (on the Omarchy machine)

```bash
tar xzf omarchy-spacex-sky.tar.gz && cd omarchy-spacex-sky
./install.sh
spacex-sky launches
spacex-sky trains
```

`install.sh` is user-only, no sudo: it copies the app to
`~/.local/share/omarchy-spacex-sky`, creates a Python venv there with
[Skyfield](https://rhodesmill.org/skyfield/), and writes the `~/.local/bin/spacex-sky`
wrapper. Caches live in `~/.cache/spacex-sky`, including a one-time ~17 MB planet
ephemeris (`de421.bsp`). Run `./uninstall.sh` to remove everything.

## Commands

```
spacex-sky launches [--florida] [-n 12] [--refresh]
spacex-sky trains   [--days 5] [--max-age 10] [--top 8] [--refresh]
spacex-sky waybar
spacex-sky notify   [--minutes 15] [--launches] [-v]
```

`--max-age 30` also shows older Starlink groups. They're more spread out and fainter,
but still fun to spot.

## Waybar

In `~/.config/waybar/config.jsonc`, add `"custom/spacex-sky"` to `modules-right` and
add this block (also in `examples/waybar-module.jsonc`):

```jsonc
"custom/spacex-sky": {
  "exec": "~/.local/bin/spacex-sky waybar",
  "return-type": "json",
  "interval": 600,
  "tooltip": true,
  "on-click": "alacritty --class spacex-sky -e bash -c 'spacex-sky launches; read -n1 -p \"Press any key to close\"'",
  "on-click-right": "alacritty --class spacex-sky -e bash -c 'spacex-sky trains; read -n1 -p \"Press any key to close\"'"
}
```

Optional colors: `examples/waybar-style.css`. Then restart Waybar (`omarchy-restart-waybar`,
or `pkill waybar && waybar &`).

## Hyprland keybinds

Add to `~/.config/hypr/bindings.conf` (see `examples/hyprland.conf`):

```ini
bindd = SUPER CTRL ALT, L, SpaceX launches, exec, alacritty --class spacex-sky -e bash -c 'spacex-sky launches; read -n1 -p "Press any key to close"'
bindd = SUPER CTRL ALT, S, Starlink trains, exec, alacritty --class spacex-sky -e bash -c 'spacex-sky trains; read -n1 -p "Press any key to close"'

windowrule = float, class:^(spacex-sky)$
windowrule = size 1000 750, class:^(spacex-sky)$
windowrule = center, class:^(spacex-sky)$
```

If you use Ghostty or Kitty instead of Alacritty, swap the terminal (both accept `--class`).
The `windowrule` lines use the Hyprland 0.48+ syntax. If `hyprctl configerrors` complains,
your Hyprland uses the newer rule syntax, so adjust them to match the other rules in
`~/.config/hypr/`.

## Notifications (optional, systemd user timer)

```bash
mkdir -p ~/.config/systemd/user
cp systemd/spacex-sky-notify.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now spacex-sky-notify.timer
# test right now:
spacex-sky notify -v --minutes 600
```

Every 5 minutes it checks for a train pass (and, with `--launches`, a Florida launch)
starting within 15 minutes, and sends one `notify-send` per event.

## Different location

```bash
export SPACEX_SKY_LAT=30.13 SPACEX_SKY_LON=-81.53 SPACEX_SKY_PLACE="Jacksonville"
```

To make that apply to Waybar and the keybinds too, put the exports at the top of
`~/.local/bin/spacex-sky`.

## How it works

- **Launches:** one request to Launch Library 2
  (`ll.thespacedevs.com/2.3.0/launches/upcoming/?lsp__id=121`, SpaceX only), cached
  for 1 hour. The free tier allows about 15 requests/hour, so this stays well under it.
  If the network or the rate limit fails, it uses the last cached copy. A pad counts as
  "Florida" when its location is Cape Canaveral SFS or Kennedy Space Center. Day/night is
  the sun's altitude at your house at launch time.
- **Trains:** CelesTrak's `last-30-days` GP (orbit) data plus SATCAT launch dates,
  cached for 2 hours, which is CelesTrak's update cadence. For each Starlink satellite
  launched in the last 10 days, Skyfield finds passes for the next 5 days and keeps the
  part where **the sun is below −6° for you**, **the satellite is in sunlight**, and it's
  at least 10° up. A pass needs to peak at **20° or higher**. Satellites from the same
  launch that pass within minutes of each other are merged into one "train". Ranking
  favors high passes, more satellites, fresher launches, and kid-friendly hours (6–9:30 PM).

## Honest limitations

- Starlink trains only look like a bright **string of pearls for the first few days**
  after launch. Within about a week they raise their orbits, spread out, and turn
  edge-on to dim themselves.
- Brand-new groups take up to about a day to appear in CelesTrak, and their early orbit
  data is the least accurate. Go out 5 minutes early.
- Brightness (magnitude) isn't modeled. Clouds, the moon and city light all matter.
- Launch times slip constantly. Anything not marked to the minute is a placeholder
  date from Launch Library.
- Morning passes often *appear* partway up the sky, when the satellites come out of
  Earth's shadow. Evening passes often *fade out* overhead, when they go into it.
