"""Command line entry point: spacex-sky {launches,trains,waybar,json,notify}."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from . import __version__, cache, launches, present, sites, trains


def cmd_launches(args):
    data = launches.fetch(refresh=args.refresh)
    cfg = sites.load_config()
    known = sites.catalog_plus(data)
    favorite_ids = set(cfg["favorites"])
    site_ids = sites.resolve_site_ids(args.site, known) if args.site else None
    bits = []
    if args.florida:
        bits.append("Florida")
    if args.favorites:
        bits.append("favorites")
    if args.site:
        bits.append(args.site)
    print(launches.render(
        data,
        florida_only=args.florida,
        limit=args.limit,
        favorites_only=args.favorites,
        favorite_ids=favorite_ids,
        site_ids=set(site_ids) if site_ids is not None else None,
        subtitle=", ".join(bits),
    ))


def cmd_trains(args):
    groups, passes = trains.compute(days=args.days, max_age_days=args.max_age, refresh=args.refresh)
    print(trains.render(groups, passes, days=args.days, top=args.top))


def cmd_waybar(args):
    """Print one JSON line for a bar module. Never crashes the bar."""
    try:
        board = present.build()
        print(json.dumps(present.waybar_payload(board)))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({
            "text": "🚀",
            "tooltip": f"spacex-sky: {exc}",
            "class": "idle",
            "alt": "idle",
        }))


def cmd_json(args):
    """Full board for the shell popup. Always prints JSON."""
    try:
        board = present.build(refresh=args.refresh)
    except Exception as exc:  # noqa: BLE001
        board = present.empty_board(f"spacex-sky: {exc}")
    print(json.dumps(board))


def _site_name(sid):
    for city in sites.cities():
        if city["id"] == sid:
            return f"{city['name']}, {city['region']}"
    for site in sites.catalog():
        if site["id"] == sid:
            return site["name"]
    return sid


def cmd_favorite(args):
    known = sites.catalog()
    if args.action == "list":
        cfg = sites.load_config()
        for sid in cfg["favorites"]:
            print(f"★ {_site_name(sid)}")
        if not cfg["favorites"]:
            print("No favorite cities.")
        return
    if args.action == "toggle":
        sid, added, favorites = sites.toggle_favorite(args.site, known)
        verb = "Favorited" if added else "Unfavorited"
    elif args.action == "add":
        sid, favorites = sites.set_favorite(args.site, True, known)
        verb = "Favorited"
    else:
        sid, favorites = sites.set_favorite(args.site, False, known)
        verb = "Unfavorited"
    names = ", ".join(_site_name(item) for item in favorites) or "(none)"
    print(f"{verb} {_site_name(sid)}")
    print(f"favorites: {names}")


def cmd_filter(args):
    if args.action == "show":
        print(sites.load_config()["filter"])
        return
    value = sites.set_filter(args.value, sites.catalog())
    print(value)


def _notify(title, body, urgency="normal"):
    try:
        subprocess.run(
            ["notify-send", "-a", "spacex-sky", "-u", urgency, title, body],
            check=False,
        )
    except FileNotFoundError:
        print(f"{title}\n{body}")


def _watched_launch(launch, favorite_ids):
    """Florida always alerts. Starred cities alert too."""
    if launch.get("site") == "FL":
        return True
    favorite_ids = set(favorite_ids or [])
    if not favorite_ids:
        return False
    city = launch.get("city_id") or sites.city_id_for(
        launch.get("site_id", ""), launch.get("site_name", ""), launch.get("site", ""))
    return city in favorite_ids or launch.get("site_id") in favorite_ids


def launch_notices(upcoming, now, sent, minutes=15, favorite_ids=None):
    """Launch alerts. One heads-up inside 12 hours, then one at liftoff lead."""
    sent = set(sent or [])
    soon = timedelta(minutes=minutes)
    day = timedelta(hours=12)
    notices = []
    for launch in upcoming:
        if not _watched_launch(launch, favorite_ids):
            continue
        net = launch["net"]
        if net < now:
            continue
        florida = launch.get("site") == "FL"
        place = launch.get("where") or ("Florida" if florida else "Launch")
        region = "Florida" if florida else (launch.get("city_name") or launch.get("site_name") or "Launch")
        mission = launch.get("mission") or "Launch"
        stamp = net.isoformat()[:16]
        name = launch.get("name") or mission
        if net <= now + day and net > now + soon:
            key = f"launch-day:{name}:{stamp}"
            if key not in sent:
                notices.append((
                    key,
                    f"🚀 {region} launch · {place}",
                    f"{mission}\n{launches.fmt_time(net)}",
                    "normal",
                ))
        if now <= net <= now + soon:
            key = f"launch:{name}:{stamp}"
            if key not in sent:
                mins = max(0, int((net - now).total_seconds() // 60))
                _tag, sentence = launches.visibility(launch)
                notices.append((
                    key,
                    f"🚀 {region} · {place} in {mins} min",
                    f"{mission}\n{sentence}",
                    "normal",
                ))
    return notices


def florida_notices(upcoming, now, sent, minutes=15):
    """Florida-only alerts. Kept for tests and older callers."""
    return launch_notices(upcoming, now, sent, minutes, favorite_ids=())


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

    # Florida always alerts. Starred cities do too. --launches remains so older timers still match.
    cfg = sites.load_config()
    favs = sites.normalize_favorites(cfg.get("favorites") or [])
    for key, title, body, urgency in launch_notices(
            launches.fetch(), now, set(sent), args.minutes, favs):
        _notify(title, body, urgency)
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
    p.add_argument("--favorites", action="store_true", help="only launches from favorite cities")
    p.add_argument("--site", help="only this site (SLC-40, LC-39A, Vandenberg, Starbase, …)")
    p.add_argument("--limit", "-n", type=int, default=12)
    p.add_argument("--refresh", action="store_true", help="ignore the 1h cache")
    p.set_defaults(func=cmd_launches)

    p = sub.add_parser("trains", help="visible Starlink train passes")
    p.add_argument("--days", type=int, default=5, help="days ahead to search (default 5)")
    p.add_argument("--max-age", type=int, default=10, help="only groups launched within N days (default 10)")
    p.add_argument("--top", type=int, default=8)
    p.add_argument("--refresh", action="store_true", help="ignore caches")
    p.set_defaults(func=cmd_trains)

    p = sub.add_parser("waybar", help="JSON for a bar module (text, tooltip, class)")
    p.set_defaults(func=cmd_waybar)

    p = sub.add_parser("json", help="full sky board as JSON for the shell popup")
    p.add_argument("--refresh", action="store_true", help="ignore caches")
    p.set_defaults(func=cmd_json)

    p = sub.add_parser("favorite", help="mark cities you care about")
    p.add_argument("action", choices=("list", "toggle", "add", "remove"))
    p.add_argument("site", nargs="?", help="city or pad (Cape Canaveral, SLC-40, Kennedy, …)")
    p.set_defaults(func=cmd_favorite)

    p = sub.add_parser("filter", help="remember the popup filter chip")
    p.add_argument("action", nargs="?", default="show", choices=("show", "set"))
    p.add_argument("value", nargs="?", help="all, favorites, or a city")
    p.set_defaults(func=cmd_filter)

    p = sub.add_parser("notify", help="desktop notification before a pass, and for Florida launches")
    p.add_argument("--minutes", type=int, default=15, help="minutes before liftoff or a pass (default 15)")
    p.add_argument("--launches", action="store_true", help="accepted for older timers; Florida alerts are always on")
    p.add_argument("--verbose", "-v", action="store_true")
    p.set_defaults(func=cmd_notify)

    args = ap.parse_args(argv)
    if getattr(args, "action", None) in ("toggle", "add", "remove") and not getattr(args, "site", None):
        ap.error("favorite needs a site name")
    if getattr(args, "action", None) == "set" and not getattr(args, "value", None):
        ap.error("filter set needs a value")
    try:
        args.func(args)
    except (RuntimeError, ValueError) as e:
        print(f"spacex-sky: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
