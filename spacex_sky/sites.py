"""Launch-site identity, favorites, and the popup filter.

Favorites and the remembered filter live in
~/.config/omarchy-spacex-sky/config.toml. A favorite is a city: Cape Canaveral
covers every Cape pad, and Kennedy covers LC-39A and LC-39B. New installs
favorite both Florida cities.
"""
import json
import os
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.11+ has tomllib
    tomllib = None

DEFAULT_FAVORITES = ("cape-canaveral", "kennedy")
FILTER_ALL = "all"
FILTER_FAVORITES = "favorites"

_PAD_RE = re.compile(
    r"(?P<style>space\s+launch\s+complex|launch\s+complex|orbital\s+launch\s+pad|slc|lc|pad)"
    r"\s*-?\s*(?P<code>\d+[a-z]?)",
    re.I,
)


def config_path():
    override = os.environ.get("SPACEX_SKY_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".config" / "omarchy-spacex-sky" / "config.toml"


def _site(sid, name, short, region, where, chip, aliases):
    return {
        "id": sid,
        "name": name,
        "short": short,
        "region": region,
        "where": where,
        "chip": chip,
        "aliases": list(aliases),
    }


def cities():
    """Places you can favorite. Pads in the same city share one star."""
    return [
        {"id": "cape-canaveral", "name": "Cape Canaveral", "region": "FL"},
        {"id": "kennedy", "name": "Kennedy", "region": "FL"},
        {"id": "vandenberg", "name": "Vandenberg", "region": "CA"},
        {"id": "starbase", "name": "Starbase", "region": "TX"},
    ]


def city_name(city_id):
    for city in cities():
        if city["id"] == city_id:
            return city["name"]
    return city_id


def city_id_for(site_id, name="", region=""):
    """Map a pad to its city. SLC-40 and any other Cape pad share Cape Canaveral."""
    sid = (site_id or "").strip().lower()
    name_l = (name or "").lower()
    region_u = (region or "").strip().upper()
    if sid in {city["id"] for city in cities()}:
        return sid
    if (sid in ("lc-39a", "lc-39b") or sid.startswith("lc-39")
            or "kennedy" in name_l or name_l.startswith("ksc")):
        return "kennedy"
    if region_u == "CA" or sid in ("vandenberg", "slc-4e", "slc-4") or "vandenberg" in name_l:
        return "vandenberg"
    if region_u == "TX" or sid == "starbase" or "starbase" in name_l or "boca chica" in name_l:
        return "starbase"
    if region_u == "FL" or "cape canaveral" in name_l or sid.startswith("slc-"):
        return "cape-canaveral"
    return sid or "unknown"


def normalize_favorites(ids):
    """Collapse pad ids onto their cities, keeping the first-seen order."""
    chosen = []
    for item in ids or []:
        city = city_id_for(str(item).strip())
        if city and city not in chosen:
            chosen.append(city)
    return chosen


def catalog():
    """Sites a person can favorite even before a launch from them is listed."""
    return [
        _site("slc-40", "Cape Canaveral SLC-40", "SLC-40", "FL",
              "Cape Canaveral SLC-40, FL", "SLC-40",
              ["slc40", "complex 40", "space launch complex 40"]),
        _site("lc-39a", "KSC LC-39A", "LC-39A", "FL",
              "KSC LC-39A, FL", "LC-39A",
              ["39a", "lc39a", "launch complex 39a", "pad 39a"]),
        _site("lc-39b", "KSC LC-39B", "LC-39B", "FL",
              "KSC LC-39B, FL", "LC-39B",
              ["39b", "lc39b", "launch complex 39b", "pad 39b"]),
        _site("vandenberg", "Vandenberg", "VAFB", "CA",
              "Vandenberg SFB, CA", "Vandenberg",
              ["vafb", "slc-4e", "slc4e", "space launch complex 4e"]),
        _site("starbase", "Starbase TX", "Starbase", "TX",
              "Starbase TX", "Starbase",
              ["boca chica", "starship", "olp-2", "orbital launch pad"]),
    ]


def region_of(location):
    loc = (location or "").lower()
    if any(w in loc for w in ("cape canaveral", "kennedy space center", ", fl")):
        return "FL"
    if "vandenberg" in loc or ", ca" in loc:
        return "CA"
    if "starbase" in loc or "boca chica" in loc or ", tx" in loc:
        return "TX"
    return "??"


def pad_parts(pad):
    """Return (style, code) like ('SLC', '40') or ('', '')."""
    match = _PAD_RE.search(pad or "")
    if not match:
        return "", ""
    style_raw = match.group("style").lower()
    code = match.group("code").upper()
    if "orbital" in style_raw:
        style = "PAD"
    elif style_raw in ("launch complex", "lc"):
        style = "LC"
    else:
        style = "SLC"
    return style, code


def _slug(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "unknown"


def site_for(pad, location):
    """Stable site for a pad. Florida pads stay separate; Vandenberg and Starbase are one chip each."""
    region = region_of(location)
    style, code = pad_parts(pad)
    code_l = code.lower()

    if code_l == "39a":
        found = _by_id("lc-39a")
        return found
    if code_l == "39b":
        return _by_id("lc-39b")
    if code_l == "40" and region == "FL":
        return _by_id("slc-40")
    if region == "CA":
        site = _by_id("vandenberg")
        if code:
            site = dict(site)
            site["short"] = f"{style}-{code}" if style in ("SLC", "LC") else code
            site["where"] = f"Vandenberg {site['short']}, CA"
        return site
    if region == "TX":
        site = _by_id("starbase")
        if code and style == "PAD":
            site = dict(site)
            site["short"] = f"OLP-{code}"
            site["where"] = "Starbase TX"
        return site
    if region == "FL" and code:
        kind = "LC" if style == "LC" or "kennedy" in (location or "").lower() else "SLC"
        if kind == "LC" or "kennedy" in (location or "").lower():
            sid = f"lc-{code_l}"
            name = f"KSC LC-{code}"
            where = f"KSC LC-{code}, FL"
        else:
            sid = f"slc-{code_l}"
            name = f"Cape Canaveral SLC-{code}"
            where = f"Cape Canaveral SLC-{code}, FL"
        return _site(sid, name, f"{kind}-{code}", "FL", where, f"{kind}-{code}", [name.lower()])
    if region == "FL":
        return _site("cape-canaveral", "Cape Canaveral", "Cape Canaveral", "FL",
                     "Cape Canaveral, FL", "Cape Canaveral", ["cape canaveral", "ccsfs"])
    label = (location or pad or "Unknown site").split(",")[0].strip() or "Unknown site"
    return _site(_slug(label), label, label, region, label, label, [])


def _by_id(sid):
    for site in catalog():
        if site["id"] == sid:
            return dict(site)
    raise KeyError(sid)


def catalog_plus(launches):
    """Canonical sites plus any pad the current launch list actually uses."""
    merged = {site["id"]: dict(site) for site in catalog()}
    for launch in launches or []:
        if launch.get("site_id") and launch.get("site_name"):
            site = {
                "id": launch["site_id"],
                "name": launch["site_name"],
                "short": launch.get("site_short") or launch["site_name"],
                "region": launch.get("site") or launch.get("region") or "??",
                "where": launch.get("where") or launch["site_name"],
                "chip": launch.get("chip") or launch.get("site_short") or launch["site_name"],
                "aliases": [],
            }
        else:
            site = site_for(launch.get("pad", ""), launch.get("location", ""))
        merged.setdefault(site["id"], site)
    return list(merged.values())


def _norm(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _region_sites(known, region):
    return [site["id"] for site in known if site["region"] == region]


def resolve_site_ids(query, known):
    """Match a --site value to one or more site ids. Raises ValueError if it is ambiguous or unknown."""
    raw = (query or "").strip().lower()
    if not raw:
        raise ValueError("Give a site name, for example SLC-40, LC-39A, Vandenberg, or Starbase.")
    folded = re.sub(r"\s+", " ", raw)
    if folded in ("florida", "fl"):
        return _need(raw, _region_sites(known, "FL"))
    if folded in ("california", "ca"):
        return _need(raw, _region_sites(known, "CA"))
    if folded in ("texas", "tx"):
        return _need(raw, _region_sites(known, "TX"))
    if folded in ("ksc", "kennedy", "kennedy space center"):
        ids = [s["id"] for s in known if s["id"].startswith("lc-39") or s["name"].lower().startswith("ksc")]
        return _need(raw, ids)
    if folded in ("cape", "cape canaveral", "ccsfs"):
        ids = [s["id"] for s in known if s["region"] == "FL" and (
            "cape canaveral" in s["name"].lower() or s["id"].startswith("slc-") or s["id"] == "cape-canaveral")]
        return _need(raw, ids)

    norm = _norm(raw)
    exact = []
    for site in known:
        keys = [site["id"], site["name"], site["short"], site.get("where", ""), site.get("chip", "")]
        keys.extend(site.get("aliases") or [])
        if raw in {k.lower() for k in keys} or norm in {_norm(k) for k in keys if k}:
            exact.append(site)
    if len(exact) == 1:
        return [exact[0]["id"]]
    if len(exact) > 1:
        ids = [site for site in exact if site["id"] == raw or _norm(site["id"]) == norm]
        if len(ids) == 1:
            return [ids[0]["id"]]
        raise ValueError(_ambiguous(raw, exact))

    partial = [site for site in known if norm and (
        norm in _norm(site["name"]) or norm in _norm(site["id"]) or norm in _norm(site["short"]))]
    if len(partial) == 1:
        return [partial[0]["id"]]
    if not partial:
        names = ", ".join(site["name"] for site in known)
        raise ValueError(f"No launch site matches {query!r}. Known sites: {names}.")
    raise ValueError(_ambiguous(raw, partial))


def resolve_one(query, known):
    """One site id. A bare slug is kept so a pad the catalog has not heard of can still be favorited."""
    try:
        ids = resolve_site_ids(query, known)
    except ValueError:
        ids = None
    if ids and len(ids) == 1:
        return ids[0]
    raw = (query or "").strip().lower()
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", raw):
        return raw
    if ids and len(ids) > 1:
        raise ValueError(_ambiguous(raw, [s for s in known if s["id"] in ids]))
    names = ", ".join(site["name"] for site in known)
    raise ValueError(f"No launch site matches {query!r}. Known sites: {names}.")


def _need(raw, ids):
    if ids:
        return ids
    raise ValueError(f"No launch sites match {raw!r}.")


def _ambiguous(raw, sites):
    names = ", ".join(site["name"] for site in sites)
    return f"{raw!r} matches more than one site: {names}."


def default_config():
    return {"favorites": list(DEFAULT_FAVORITES), "filter": FILTER_ALL}


def load_config():
    path = config_path()
    if not path.exists():
        cfg = default_config()
        try:
            save_config(cfg)
        except OSError:
            pass
        return cfg
    if tomllib is None:
        return default_config()
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return default_config()
    favorites = data.get("favorites", list(DEFAULT_FAVORITES))
    if not isinstance(favorites, list):
        favorites = list(DEFAULT_FAVORITES)
    raw_favorites = [str(item).strip() for item in favorites if str(item).strip()]
    favorites = normalize_favorites(raw_favorites)
    filt = data.get("filter", FILTER_ALL)
    if not isinstance(filt, str) or not filt.strip():
        filt = FILTER_ALL
    filt = _migrate_filter(filt.strip())
    cfg = {"favorites": favorites, "filter": filt}
    if favorites != raw_favorites or filt != data.get("filter", FILTER_ALL):
        try:
            save_config(cfg)
        except OSError:
            pass
    return cfg


def save_config(cfg):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    favorites = ", ".join(json.dumps(item) for item in cfg["favorites"])
    text = (
        "# Favorite cities for the sky board and `spacex-sky launches --favorites`.\n"
        "# Pads in one city share a star. Cape Canaveral covers SLC-40 and the other Cape pads.\n"
        f"favorites = [{favorites}]\n"
        "\n"
        "# Popup filter: \"all\", \"favorites\", or a city id "
        "(cape-canaveral, kennedy, vandenberg, starbase).\n"
        f"filter = {json.dumps(cfg['filter'])}\n"
    )
    path.write_text(text)


def _migrate_filter(filt):
    raw = (filt or FILTER_ALL).strip()
    folded = raw.lower()
    if folded in (FILTER_ALL, FILTER_FAVORITES, "favourite", "fav", "favorite", "everything", "*"):
        if folded in ("favourite", "fav", "favorite"):
            return FILTER_FAVORITES
        if folded in ("everything", "*"):
            return FILTER_ALL
        return folded
    return city_id_for(folded)


def favorite_target(query, known=None):
    """The city a favorite or popup filter refers to, even if the query names one pad."""
    known = known if known is not None else catalog()
    raw = (query or "").strip().lower()
    for city in cities():
        names = {city["id"], city["name"].lower(), f"{city['name']}, {city['region']}".lower()}
        if raw in names:
            return city["id"]
    sid = resolve_one(query, known)
    site = next((item for item in known if item["id"] == sid), None)
    if site:
        return city_id_for(site["id"], site.get("name", ""), site.get("region", ""))
    return city_id_for(sid)


def toggle_favorite(query, known=None):
    known = known if known is not None else catalog()
    sid = favorite_target(query, known)
    cfg = load_config()
    favorites = list(cfg["favorites"])
    added = sid not in favorites
    if added:
        favorites.append(sid)
    else:
        favorites = [item for item in favorites if item != sid]
    cfg["favorites"] = favorites
    save_config(cfg)
    return sid, added, favorites


def set_favorite(query, added, known=None):
    known = known if known is not None else catalog()
    sid = favorite_target(query, known)
    cfg = load_config()
    favorites = [item for item in cfg["favorites"] if item != sid]
    if added:
        favorites.append(sid)
    cfg["favorites"] = favorites
    save_config(cfg)
    return sid, favorites


def set_filter(query, known=None):
    known = known if known is not None else catalog()
    raw = (query or "").strip().lower()
    if raw in (FILTER_ALL, "everything", "*"):
        value = FILTER_ALL
    elif raw in (FILTER_FAVORITES, "favourite", "fav", "favorite"):
        value = FILTER_FAVORITES
    else:
        value = favorite_target(query, known)
    cfg = load_config()
    cfg["filter"] = value
    save_config(cfg)
    return value


def active_filter(cfg, known_ids):
    filt = (cfg or {}).get("filter") or FILTER_ALL
    if filt in (FILTER_ALL, FILTER_FAVORITES) or filt in known_ids:
        return filt
    return FILTER_ALL
