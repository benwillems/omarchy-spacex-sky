"""Command line entry point: spacex-sky {launches,trains,waybar,notify}."""
import argparse
import html
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from . import __version__, cache, config, launches, trains


def cmd_launches(args):
    data = launches.fetch(refresh=args.refresh)
    print(launches.render(data, florida_only=args.florida, limit=args.limit))


def cmd_trains(args):
    groups, passes = trains.compute(days=args.days, max_age_days=args.max_age, refresh=args.refresh)
    print(trains.render(groups, passes, days=args.days, top=args.top))


def _tonight_end(now_local):
    """'Tonight' = until 8 AM tomorrow (or this morning if it's still before 8 AM)."""
    end = now_local.replace(hour=8, minute=0, second=0, microsecond=0)
    return end if now_local < end else end + timedelta(days=1)


def cmd_waybar(args):
    """Print one JSON line for a Waybar custom module. Never crashes Waybar."""
    now = datetime.now(timezone.utc)
    text, tip, cls = "🚀", [], "idle"
    try:
        fl = [l for l in launches.fetch() if l["site"] == "FL" and l["net"] > now]
        if fl:
            nxt = fl[0]
            text = f"🚀 FL {launches.countdown(nxt['net'], now)}"
            cls = "launch"
            tip.append(f"Next Florida launch: {nxt['mission']} ({nxt['rocket']})")
            tip.append(f"  {launches.fmt_time(nxt['net'])} from {nxt['pad']}")
            tip.append(f"  {launches.visibility(nxt)[1]}")
    except Exception as e:  # noqa: BLE001
        tip.append(f"Launch data unavailable: {e}")
    try:
        _, passes = trains.compute()
        end = _tonight_end(now.astimezone(config.TZ))
        tonight = sorted((p for p in passes if p["start"].astimezone(config.TZ) < end),
                         key=lambda p: p["start"])
        if tonight:
            best = max(tonight, key=trains.score)
            local = best["start"].astimezone(config.TZ).strftime("%-I:%M%p").lower()
            text = f"★ {local}  " + text
            cls = "train"
            tip.append("")
            tip.append(f"Starlink train coming up: {trains.fmt_time(best['start'])}")
            tip.append(f"  peak {best['peak_alt']:.0f}°, starts {best['start_dir']}, ends {best['end_dir']}")
            tip.append(f"  {trains.kid_line(best)}")
    except Exception as e:  # noqa: BLE001
        tip.append(f"Starlink data unavailable: {e}")
    tip.append("")
    tip.append("Click: launch list · Right-click: Starlink trains")
    # Waybar tooltips are Pango markup, so escape &, < and >.
    print(json.dumps({"text": text, "tooltip": html.escape("\n".join(tip), quote=False), "class": cls, "alt": cls}))


def _notify(title, body):
    try:
        subprocess.run(["notify-send", "-a", "spacex-sky", "-u", "normal", title, body], check=False)
    except FileNotFoundError:
        print(f"{title}\n{body}")


def cmd_notify(args):
    """Meant to run every 5 min from a systemd user timer. Notifies once per event."""
    now = datetime.now(timezone.utc)
    lead = timedelta(minutes=args.minutes)
    sent = cache.read_cache("notified.json", 7 * 86400) or []
    new = []

    _, passes = trains.compute()
    for p in passes:
        key = f"train:{p['group']}:{p['start'].isoformat()[:16]}"
        if key not in sent and now <= p["start"] <= now + lead:
            mins = int((p["start"] - now).total_seconds() // 60)
            _notify(f"★ Starlink train in {mins} min!",
                    f"{trains.fmt_time(p['start'])} · peak {p['peak_alt']:.0f}°\n{trains.kid_line(p)}")
            new.append(key)

    if args.launches:
        for l in launches.fetch():
            key = f"launch:{l['name']}:{l['net'].isoformat()[:16]}"
            if l["site"] == "FL" and key not in sent and now <= l["net"] <= now + lead:
                mins = int((l["net"] - now).total_seconds() // 60)
                _notify(f"🚀 Florida launch in {mins} min: {l['mission']}", launches.visibility(l)[1])
                new.append(key)

    if new:
        cache.write_cache("notified.json", (sent + new)[-200:])
    elif args.verbose:
        print(f"Nothing new to notify in the next {args.minutes} minutes.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="spacex-sky", description=__doc__)
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("launches", help="upcoming SpaceX launches, Florida ones marked")
    p.add_argument("--florida", "-f", action="store_true", help="only Florida launches")
    p.add_argument("--limit", "-n", type=int, default=12)
    p.add_argument("--refresh", action="store_true", help="ignore the 1h cache")
    p.set_defaults(func=cmd_launches)

    p = sub.add_parser("trains", help="visible Starlink train passes")
    p.add_argument("--days", type=int, default=5, help="days ahead to search (default 5)")
    p.add_argument("--max-age", type=int, default=10, help="only groups launched within N days (default 10)")
    p.add_argument("--top", type=int, default=8)
    p.add_argument("--refresh", action="store_true", help="ignore caches")
    p.set_defaults(func=cmd_trains)

    p = sub.add_parser("waybar", help="JSON for a Waybar custom module")
    p.set_defaults(func=cmd_waybar)

    p = sub.add_parser("notify", help="desktop notification shortly before a pass/launch")
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--launches", action="store_true", help="also notify for Florida launches")
    p.add_argument("--verbose", "-v", action="store_true")
    p.set_defaults(func=cmd_notify)

    args = ap.parse_args(argv)
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"spacex-sky: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
