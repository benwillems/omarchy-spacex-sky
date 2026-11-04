# SpaceX Sky

Omarchy bar widget for watching SpaceX from the backyard with the kids.
The rocket in the bar is the next thing to walk outside for: a Florida
launch, a Starlink train, or another pad you starred. Click it for the
sky board — where to look, a compass, and a webcast link.

Plugin id: `bjw.spacex-sky`. Defaults to Jacksonville, FL
(30.13 N, 81.53 W) in America/New_York.

## Install

The widget is an Omarchy shell plugin. The launch and train data comes
from a small Python helper that needs [Skyfield](https://rhodesmill.org/skyfield/).

```bash
omarchy plugin add https://github.com/benwillems/omarchy-spacex-sky.git --enable
~/.config/omarchy/plugins/bjw.spacex-sky/install.sh
omarchy restart shell
```

`install.sh` is user-only (no sudo). It creates a venv in
`~/.local/share/omarchy-spacex-sky`, installs Skyfield, and writes
`~/.local/bin/spacex-sky`. Caches live in `~/.cache/spacex-sky`,
including a one-time ~17 MB planet ephemeris (`de421.bsp`).

Move the widget with:

```bash
omarchy bar move bjw.spacex-sky --section center
```

## Remove

```bash
omarchy plugin remove bjw.spacex-sky
~/.config/omarchy/plugins/bjw.spacex-sky/uninstall.sh
```

If the plugin folder is already gone, run `uninstall.sh` from a clone of
this repository. Favorites in `~/.config/omarchy-spacex-sky/` are left in
place.

## Usage

Click the rocket for the sky board. Tap a city to filter, tap its star
for alerts. Cape Canaveral is one star for every Cape pad; Kennedy is one
star for LC-39A and LC-39B. Each launch still names its pad.

The bar shows the hero (`Cape · SLC-40`, or `★ 7:16pm` for a train).
Florida is a second beat only when that is a different event. Date-only
NETs print the calendar day instead of a fake countdown.

```
spacex-sky launches [--florida] [--favorites] [--site NAME] [-n 12] [--refresh]
spacex-sky trains   [--days 5] [--max-age 10] [--top 8] [--refresh]
spacex-sky json     [--refresh]
spacex-sky favorite list | toggle NAME | add NAME | remove NAME
spacex-sky filter [show] | set all|favorites|NAME
spacex-sky notify   [--minutes 15] [--launches] [-v]
```

New helper installs favorite Cape Canaveral and Kennedy. Star or unstar
cities in the popup, or with `favorite toggle`.

## Dependencies

- Omarchy Quattro shell (Quickshell)
- `python3` and a working venv (`python -m venv`)
- Skyfield (installed into the user venv by `install.sh`)
- Launch Library 2 (`ll.thespacedevs.com`, SpaceX agency id 121)
- CelesTrak GP and SATCAT data for Starlink trains
- `notify-send` only if you enable the optional alert timer

No root, no system packages beyond Python, and no edits under
`/usr/share/omarchy/`.

## Optional alerts

`install.sh` does not enable a timer. To get a desktop notification 15
minutes before a Starlink pass, when a Florida launch (or a launch from a
starred city) is inside 12 hours, and 15 minutes before that liftoff:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/spacex-sky-notify.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now spacex-sky-notify.timer
```

Florida always alerts, even if those cities are unstarred.

## Different location

```bash
export SPACEX_SKY_LAT=30.13 SPACEX_SKY_LON=-81.53 SPACEX_SKY_PLACE="Jacksonville"
```

Put those exports at the top of `~/.local/bin/spacex-sky` to apply them
to the bar as well.

## License

MIT. See [LICENSE](LICENSE).
