"""Upcoming SpaceX launches from Launch Library 2 (thespacedevs.com)."""
from datetime import datetime, timezone

from . import cache, config, sites, sky

_TIME_SET = {"Minute", "Second", "Hour", ""}


def fetch(refresh=False):
    # SpaceX's LL2 agency id is 121. One request, cached for an hour.
    url = (f"{config.LL2_BASE}/launches/upcoming/"
           "?lsp__id=121&limit=25&mode=normal&ordering=net")
    data = cache.fetch_json(url, "ll2_upcoming_spacex.json",
                            config.LAUNCH_CACHE_SECONDS, refresh=refresh)
    return [parse(r) for r in data.get("results", [])]


def site_of(location_name):
    return sites.region_of(location_name)


def time_is_set(precision):
    return (precision or "") in _TIME_SET


def _webcast(record):
    """Official stream if Launch Library has one, otherwise SpaceX launches."""
    for key in ("vidURLs", "vid_urls"):
        for item in record.get(key) or []:
            if isinstance(item, dict) and item.get("url"):
                return item["url"]
            if isinstance(item, str) and item.startswith("http"):
                return item
    if record.get("webcast_live"):
        return "https://www.youtube.com/@SpaceX/live"
    return "https://www.spacex.com/launches/"


def parse(r):
    pad = r.get("pad") or {}
    loc = (pad.get("location") or {}).get("name", "")
    net = datetime.fromisoformat(r["net"].replace("Z", "+00:00"))
    mission = (r.get("mission") or {}).get("name") or r["name"].split("|")[-1].strip()
    rocket = ((r.get("rocket") or {}).get("configuration") or {}).get("name", "?")
    pad_name = pad.get("name", "?")
    site = sites.site_for(pad_name, loc)
    return {
        "name": r["name"],
        "mission": mission,
        "rocket": rocket,
        "net": net,
        "precision": (r.get("net_precision") or {}).get("name", ""),
        "status": (r.get("status") or {}).get("abbrev", ""),
        "pad": pad_name,
        "location": loc,
        "site": site["region"] if site["region"] in ("FL", "CA", "TX") else site_of(loc),
        "site_id": site["id"],
        "site_name": site["name"],
        "site_short": site["short"],
        "chip": site["chip"],
        "where": site["where"],
        "lat": float(pad["latitude"]) if pad.get("latitude") else None,
        "lon": float(pad["longitude"]) if pad.get("longitude") else None,
        "probability": r.get("probability"),
        "webcast": _webcast(r),
    }


def look_dir(direction, miles):
    return (f"look {direction} (~{miles:.0f} mi away); it pops above the trees "
            "about a minute after liftoff")


def details(launch):
    """Kid-facing look direction and whether the launch can be seen from home."""
    if launch["site"] != "FL" or launch["lat"] is None:
        where = {"CA": "California", "TX": "Texas"}.get(launch["site"], "somewhere far")
        sentence = f"Not visible from {config.PLACE} ({where}). Watch the webcast."
        return {
            "visible": False,
            "tag": "no",
            "sentence": sentence,
            "can_we_see": f"No — {where} is too far. Watch the webcast.",
            "look_dir": "",
            "look_words": "",
            "look_az": 0,
            "miles": None,
        }
    brg, miles = sky.bearing_and_miles(config.LAT, config.LON, launch["lat"], launch["lon"])
    compass = sky.compass(brg)
    words = sky.COMPASS_WORDS[compass]
    look = look_dir(words, miles)
    base = {
        "visible": True,
        "look_dir": compass,
        "look_words": words,
        "look_az": round(brg),
        "miles": round(miles),
    }
    if not time_is_set(launch.get("precision", "")):
        base.update({
            "tag": "TBD",
            "sentence": f"Yes if the sky is clear: {look}. Exact time not set yet.",
            "can_we_see": f"Yes if it's clear — look {compass}. Time isn't set yet.",
        })
        return base
    sun = float(sky.sun_altitude(sky.timescale().from_datetime(launch["net"])))
    if sun < -18:
        base.update({
            "tag": "NIGHT",
            "sentence": f"Night launch, best kind! A bright moving flame; {look}.",
            "can_we_see": f"Yes — look {compass}. Night launch, the bright one.",
        })
    elif sun < 0:
        base.update({
            "tag": "TWILIGHT",
            "sentence": f"Twilight launch: watch for a glowing 'space jellyfish' plume; {look}.",
            "can_we_see": f"Yes — look {compass}. Twilight: watch for the jellyfish.",
        })
    else:
        base.update({
            "tag": "day",
            "sentence": f"Daytime: maybe a faint white dot/contrail if it's clear; {look}.",
            "can_we_see": f"Maybe — look {compass}. Daytime, so it may be faint.",
        })
    return base


def visibility(launch):
    """Return (short tag, sentence) about seeing it from home."""
    info = details(launch)
    return info["tag"], info["sentence"]


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


def render(launches, florida_only=False, limit=12, favorites_only=False, favorite_ids=None,
           site_ids=None, subtitle=""):
    out = []
    now = datetime.now(timezone.utc)
    favorite_ids = set(favorite_ids or [])
    shown = [l for l in launches if l["net"] > now or (now - l["net"]).total_seconds() < 3600]
    if florida_only:
        shown = [l for l in shown if l["site"] == "FL"]
    if favorites_only:
        cities = set(sites.normalize_favorites(favorite_ids))
        shown = [l for l in shown if sites.city_id_for(
            l.get("site_id"), l.get("site_name"), l.get("site")) in cities]
    if site_ids is not None:
        shown = [l for l in shown if l.get("site_id") in site_ids]
    shown = shown[:limit]
    title = f"Upcoming SpaceX launches (times in {config.TZ_LABEL}, seen from {config.PLACE})"
    if subtitle:
        title += f" — {subtitle}"
    out.append(title)
    out.append("=" * 72)
    if not shown:
        out.append("No upcoming launches found.")
    for l in shown:
        badge = {"FL": "🌴 FLORIDA", "CA": "   CALIFORNIA", "TX": "   TEXAS"}.get(l["site"], "   OTHER")
        tag, sentence = visibility(l)
        approx = "" if time_is_set(l["precision"]) else f" (time is approx: {l['precision']})"
        width = 13 if l["site"] == "FL" else 14  # the palm emoji is 2 columns wide
        out.append(f"{badge:<{width}} {fmt_time(l['net'])}  (in {countdown(l['net'], now)}){approx}")
        out.append(f"   {l['mission']}  ·  {l['rocket']}  ·  status: {l['status']}"
                   + (f"  ·  weather go: {l['probability']}%" if l["probability"] is not None else ""))
        star = "  ★ favorite" if sites.city_id_for(
            l.get("site_id"), l.get("site_name"), l.get("site")) in sites.normalize_favorites(favorite_ids) else ""
        out.append(f"   Pad: {l['pad']}, {l['location']}{star}")
        mark = "👀 VISIBLE?" if l["site"] == "FL" else "   visible?"
        out.append(f"   {mark} {sentence}")
        out.append("")
    out.append("Tip: launches slip a lot. Re-check the day of, and Florida night launches are the showstoppers.")
    return "\n".join(out)
