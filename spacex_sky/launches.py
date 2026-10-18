"""Upcoming SpaceX launches from Launch Library 2 (thespacedevs.com)."""
from datetime import datetime, timezone

from . import cache, config, sky

FLORIDA_WORDS = ("cape canaveral", "kennedy space center", ", fl")


def fetch(refresh=False):
    # SpaceX's LL2 agency id is 121. One request, cached for an hour.
    url = (f"{config.LL2_BASE}/launches/upcoming/"
           "?lsp__id=121&limit=25&mode=normal&ordering=net")
    data = cache.fetch_json(url, "ll2_upcoming_spacex.json",
                            config.LAUNCH_CACHE_SECONDS, refresh=refresh)
    return [parse(r) for r in data.get("results", [])]


def site_of(location_name):
    name = location_name.lower()
    if any(w in name for w in FLORIDA_WORDS):
        return "FL"
    if "vandenberg" in name or ", ca" in name:
        return "CA"
    if "starbase" in name or ", tx" in name or "boca chica" in name:
        return "TX"
    return "??"


def parse(r):
    pad = r.get("pad") or {}
    loc = (pad.get("location") or {}).get("name", "")
    net = datetime.fromisoformat(r["net"].replace("Z", "+00:00"))
    mission = (r.get("mission") or {}).get("name") or r["name"].split("|")[-1].strip()
    rocket = ((r.get("rocket") or {}).get("configuration") or {}).get("name", "?")
    return {
        "name": r["name"],
        "mission": mission,
        "rocket": rocket,
        "net": net,
        "precision": (r.get("net_precision") or {}).get("name", ""),
        "status": (r.get("status") or {}).get("abbrev", ""),
        "pad": pad.get("name", "?"),
        "location": loc,
        "site": site_of(loc),
        "lat": float(pad["latitude"]) if pad.get("latitude") else None,
        "lon": float(pad["longitude"]) if pad.get("longitude") else None,
        "probability": r.get("probability"),
    }


def look_dir(direction, miles):
    return (f"look {direction} (~{miles:.0f} mi away); it pops above the trees "
            "about a minute after liftoff")


def visibility(launch):
    """Return (short tag, sentence) about seeing it from home."""
    if launch["site"] != "FL" or launch["lat"] is None:
        where = {"CA": "California", "TX": "Texas"}.get(launch["site"], "far away")
        return "no", f"Not visible from {config.PLACE} ({where}). Watch the webcast."
    brg, miles = sky.bearing_and_miles(config.LAT, config.LON, launch["lat"], launch["lon"])
    direction = sky.COMPASS_WORDS[sky.compass(brg)]
    if launch["precision"] not in ("Minute", "Second", "Hour", ""):
        return "TBD", f"Yes if the sky is clear: {look_dir(direction, miles)}. Exact time not set yet."
    ts = sky.timescale()
    sun = float(sky.sun_altitude(ts.from_datetime(launch["net"])))
    look = look_dir(direction, miles)
    if sun < -18:
        return "NIGHT", f"Night launch, best kind! A bright moving flame; {look}."
    if sun < 0:
        return "TWILIGHT", (f"Twilight launch: watch for a glowing 'space jellyfish' plume; {look}.")
    return "day", f"Daytime: maybe a faint white dot/contrail if it's clear; {look}."


def fmt_time(dt):
    local = dt.astimezone(config.TZ)
    return local.strftime("%a %b %d %I:%M %p").replace(" 0", "  ") + f" {config.TZ_LABEL}"


def countdown(dt, now=None):
    now = now or datetime.now(timezone.utc)
    secs = int((dt - now).total_seconds())
    if secs < 0:
        return "now"
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def render(launches, florida_only=False, limit=12):
    out = []
    now = datetime.now(timezone.utc)
    shown = [l for l in launches if l["net"] > now or (now - l["net"]).total_seconds() < 3600]
    if florida_only:
        shown = [l for l in shown if l["site"] == "FL"]
    shown = shown[:limit]
    out.append(f"Upcoming SpaceX launches (times in {config.TZ_LABEL}, seen from {config.PLACE})")
    out.append("=" * 72)
    if not shown:
        out.append("No upcoming launches found.")
    for l in shown:
        badge = {"FL": "🌴 FLORIDA", "CA": "   CALIFORNIA", "TX": "   TEXAS"}.get(l["site"], "   OTHER")
        tag, sentence = visibility(l)
        approx = "" if l["precision"] in ("Minute", "Second", "") else f" (time is approx: {l['precision']})"
        width = 13 if l["site"] == "FL" else 14  # the palm emoji is 2 columns wide
        out.append(f"{badge:<{width}} {fmt_time(l['net'])}  (in {countdown(l['net'], now)}){approx}")
        out.append(f"   {l['mission']}  ·  {l['rocket']}  ·  status: {l['status']}"
                   + (f"  ·  weather go: {l['probability']}%" if l["probability"] is not None else ""))
        out.append(f"   Pad: {l['pad']}, {l['location']}")
        mark = "👀 VISIBLE?" if l["site"] == "FL" else "   visible?"
        out.append(f"   {mark} {sentence}")
        out.append("")
    out.append("Tip: launches slip a lot. Re-check the day of, and Florida night launches are the showstoppers.")
    return "\n".join(out)
