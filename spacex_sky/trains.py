"""Visible Starlink 'train' passes for recently launched groups.

How it works:
  1. Download CelesTrak's "last-30-days" orbit data (GP/OMM JSON) and the
     matching SATCAT records (for launch dates). Cached ~2 h.
  2. Keep Starlink satellites launched in the last N days, grouped by launch.
  3. For every satellite, find passes over the observer for the next few days
     and keep the part where: the sky is dark for us (sun below -6 deg), the
     satellite is still in sunlight, and it's at least 10 deg up.
  4. Merge passes of satellites from the same launch that happen within a few
     minutes of each other -> that's the "train".
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import numpy as np
from skyfield.api import EarthSatellite

from . import cache, config, sky

MIN_ALT_VISIBLE = 10.0      # deg: below this, trees and haze hide it
MIN_PEAK_ALT = 20.0         # deg: a pass must climb at least this high
SUN_LIMIT = -6.0            # deg: civil twilight over -> dark enough
TRAIN_GAP_MIN = 12          # minutes between sats that still count as one train
STEP_S = 5                  # sampling step inside a pass


def load_groups(max_age_days=10, min_age_days=0, refresh=False):
    gp = cache.fetch_json(config.CELESTRAK_GP, "celestrak_last30_gp.json",
                          config.GP_CACHE_SECONDS, refresh=refresh)
    try:
        satcat = cache.fetch_json(config.CELESTRAK_SATCAT, "celestrak_last30_satcat.json",
                                  config.GP_CACHE_SECONDS, refresh=refresh)
    except RuntimeError:
        satcat = []
    launch_dates = {r["OBJECT_ID"][:8]: r["LAUNCH_DATE"] for r in satcat if r.get("LAUNCH_DATE")}

    today = datetime.now(timezone.utc).date()
    groups = defaultdict(list)
    for rec in gp:
        if not rec.get("OBJECT_NAME", "").startswith("STARLINK"):
            continue
        groups[rec["OBJECT_ID"][:8]].append(rec)  # e.g. "2026-232"

    out = []
    for cospar, recs in groups.items():
        if cospar in launch_dates:
            launched = date.fromisoformat(launch_dates[cospar])
        else:  # estimate from orbit count: revs / revs-per-day
            r = recs[0]
            days = r["REV_AT_EPOCH"] / r["MEAN_MOTION"]
            launched = (datetime.fromisoformat(r["EPOCH"]) - timedelta(days=days)).date()
        age = (today - launched).days
        if min_age_days <= age <= max_age_days:
            out.append({"cospar": cospar, "launched": launched, "age_days": age, "records": recs})
    return sorted(out, key=lambda g: g["launched"], reverse=True)


def _visible_segment(sat, t_rise, t_set, ts, eph, topos):
    """Sample one pass; return dict for the visible part, or None."""
    secs = max(int((t_set - t_rise) * 86400), STEP_S)
    t = ts.tt_jd(t_rise.tt + np.arange(0, secs + 1, STEP_S) / 86400.0)
    alt, az, _ = (sat - topos).at(t).altaz()
    alt, az = alt.degrees, az.degrees
    sunlit = sat.at(t).is_sunlit(eph)
    sun_alt = sky.sun_altitude(t)
    vis = (alt >= MIN_ALT_VISIBLE) & sunlit & (sun_alt < SUN_LIMIT)
    if not vis.any():
        return None
    idx = np.nonzero(vis)[0]
    i0, i1 = idx[0], idx[-1]
    peak = idx[np.argmax(alt[idx])]
    if alt[peak] < MIN_PEAK_ALT:
        return None
    return {
        "start": t[i0].utc_datetime(), "end": t[i1].utc_datetime(),
        "start_az": float(az[i0]), "end_az": float(az[i1]),
        "start_alt": float(alt[i0]), "end_alt": float(alt[i1]),
        "peak_alt": float(alt[peak]), "peak_az": float(az[peak]),
        "fades": bool(not sunlit[i1] and alt[i1] > MIN_ALT_VISIBLE + 1),               # enters shadow
        "emerges": bool(not sunlit[max(i0 - 1, 0)] and alt[i0] > MIN_ALT_VISIBLE + 1),  # leaves shadow
    }


def passes_for_group(group, days=5):
    ts, eph, topos = sky.timescale(), sky.ephemeris(), sky.observer()
    now = datetime.now(timezone.utc)
    t0, t1 = ts.from_datetime(now), ts.from_datetime(now + timedelta(days=days))
    found = []
    for rec in group["records"]:
        sat = EarthSatellite.from_omm(ts, rec)
        t, ev = sat.find_events(topos, t0, t1, altitude_degrees=MIN_ALT_VISIBLE)
        rise = None
        for ti, e in zip(t, ev):
            if e == 0:
                rise = ti
            elif e == 2 and rise is not None:
                seg = _visible_segment(sat, rise, ti, ts, eph, topos)
                if seg:
                    seg["sat"] = rec["OBJECT_NAME"]
                    found.append(seg)
                rise = None
    return _merge_trains(found, group)


def _merge_trains(segments, group):
    segments.sort(key=lambda s: s["start"])
    trains, cur = [], []
    for s in segments:
        if cur and (s["start"] - cur[-1]["start"]) > timedelta(minutes=TRAIN_GAP_MIN):
            trains.append(cur)
            cur = []
        cur.append(s)
    if cur:
        trains.append(cur)

    out = []
    for sats in trains:
        lead = sats[0]
        last = max(sats, key=lambda s: s["end"])
        pass_age = (lead["start"].date() - group["launched"]).days
        out.append({
            "group": group["cospar"], "launched": group["launched"].isoformat(),
            "age_at_pass": pass_age, "count": len(sats), "group_size": len(group["records"]),
            "start": lead["start"], "end": last["end"],
            "start_dir": sky.compass(lead["start_az"]), "end_dir": sky.compass(lead["end_az"]),
            "start_alt": lead["start_alt"], "end_alt": lead["end_alt"],
            "peak_alt": lead["peak_alt"], "peak_dir": sky.compass(lead["peak_az"]),
            "one_sat_seconds": (lead["end"] - lead["start"]).total_seconds(),
            "train_minutes": (last["end"] - lead["start"]).total_seconds() / 60,
            "fades": lead["fades"], "emerges": lead["emerges"],
        })
    return out


def score(p):
    """Higher is better: high in the sky, lots of sats, young train, kid-friendly hour."""
    local = p["start"].astimezone(config.TZ)
    kid_hour = 18 <= local.hour + local.minute / 60 <= 21.5
    return (p["peak_alt"]
            + min(p["count"], 30)
            - 5 * p["age_at_pass"]
            + (15 if kid_hour else 0))


def compute(days=5, max_age_days=10, refresh=False):
    """Return (groups, ranked passes). Cached for an hour."""
    key = f"passes_{days}d_{max_age_days}a_{config.LAT:.2f}_{config.LON:.2f}.json"
    cached = None if refresh else cache.read_cache(key, config.PASS_CACHE_SECONDS)
    if cached is not None:
        for p in cached["passes"]:
            for k in ("start", "end"):
                p[k] = datetime.fromisoformat(p[k])
        now = datetime.now(timezone.utc)
        cached["passes"] = [p for p in cached["passes"] if p["end"] > now]
        return cached["groups"], cached["passes"]

    groups = load_groups(max_age_days=max_age_days, refresh=refresh)
    passes = []
    for g in groups:
        passes.extend(passes_for_group(g, days=days))
    passes.sort(key=score, reverse=True)
    summary = [{"cospar": g["cospar"], "launched": g["launched"].isoformat(),
                "age_days": g["age_days"], "count": len(g["records"])} for g in groups]
    serial = [dict(p, start=p["start"].isoformat(), end=p["end"].isoformat()) for p in passes]
    cache.write_cache(key, {"groups": summary, "passes": serial})
    return summary, passes


def fmt_time(dt):
    return dt.astimezone(config.TZ).strftime("%a %b %d %I:%M %p").replace(" 0", "  ") + f" {config.TZ_LABEL}"


def _height_words(alt):
    if alt >= 70:
        return "almost straight overhead"
    if alt >= 50:
        return "high up, two-thirds of the way to straight overhead"
    if alt >= 35:
        return "about halfway up the sky"
    return "low, a couple of fists above the trees"


def when_tag(p):
    local = p["start"].astimezone(config.TZ)
    h = local.hour + local.minute / 60
    if 18 <= h <= 21.5:
        return "⭐ kid-friendly evening"
    if 21.5 < h or h < 4.5:
        return "🌙 late night"
    if 4.5 <= h < 8:
        return "🌅 early morning, before school"
    return ""


def kid_line(p):
    start = sky.COMPASS_WORDS[p["start_dir"]]
    end = sky.COMPASS_WORDS[p["end_dir"]]
    what = (f"a line of up to {p['count']} 'moving stars'" if p["count"] > 1
            else "a 'moving star'")
    if p["emerges"]:
        line = (f"Look {start}, {_height_words(p['start_alt'])}: {what} will switch on out of "
                f"Earth's shadow and glide toward the {end}.")
    else:
        line = (f"Face the {start}: {what} passes {_height_words(p['peak_alt'])} "
                f"and heads toward the {end}.")
    if p["fades"]:
        line += " Watch them blink out one by one as they fly into Earth's shadow!"
    return line


def brightness_note(age):
    if age <= 3:
        return "very fresh: should look like a tight, bright string of pearls"
    if age <= 7:
        return "a few days old: still a line, getting fainter and more spread out"
    return "over a week old: likely faint and spread out; may need dark skies"


def render(groups, passes, days=5, top=8):
    out = [f"Starlink train passes over {config.PLACE} — next {days} days (times in {config.TZ_LABEL})",
           "=" * 78]
    if not groups:
        out.append("No Starlink groups launched in the last 10 days are in CelesTrak's catalog yet.")
        out.append("New groups usually show up within a day of launch. Check after the next Starlink launch:")
        out.append("  spacex-sky launches")
        return "\n".join(out)
    out.append("Recent Starlink launches being tracked:")
    for g in groups:
        out.append(f"  • {g['cospar']}  launched {g['launched']} ({g['age_days']} days ago), "
                   f"{g['count']} satellites — {brightness_note(g['age_days'])}")
    out.append("")
    if not passes:
        out.append("No good passes found (needs dark sky for us + sunlight on the sats + 20°+ high).")
    for i, p in enumerate(passes[:top], 1):
        mins, secs = divmod(int(p["one_sat_seconds"]), 60)
        out.append(f"#{i}  {fmt_time(p['start'])}   peak {p['peak_alt']:.0f}° in the {p['peak_dir']}   {when_tag(p)}")
        if p["emerges"]:
            begin = f"Appears {p['start_alt']:.0f}° up in the {p['start_dir']} (comes out of Earth's shadow)"
        else:
            begin = f"Rises in the {p['start_dir']}"
        if p["fades"]:
            finish = f"fades out {p['end_alt']:.0f}° up in the {p['end_dir']} (enters Earth's shadow)"
        else:
            finish = f"ends low in the {p['end_dir']}"
        out.append(f"    {begin}  →  {finish}")
        dur = f"each sat ~{mins}m{secs:02d}s"
        if p["count"] > 1:
            dur += f"; whole train ~{p['train_minutes']:.0f} min ({p['count']} of {p['group_size']} sats)"
        out.append(f"    Duration: {dur}   [group {p['group']}, {p['age_at_pass']} days after launch]")
        if p["count"] > 1 and p["train_minutes"] > 15:
            out.append("    (Spread out: expect one sat every minute or two, not a tight line.)")
        out.append(f"    🧒 {kid_line(p)}")
        out.append("")
    out.append("Honest fine print: the 'string of pearls' only looks like a bright line for the first")
    out.append("few days after launch. After about a week the satellites raise their orbits, spread out,")
    out.append("and turn edge-on to dim themselves. Predictions can drift by a minute or two, so go out")
    out.append("5 minutes early and give your eyes time to adjust. Clouds win every time.")
    return "\n".join(out)
