"""Structured sky board: hero event, launch cards, train cards, bar text.

The hero is the next thing to walk outside for. A favorite-site launch wins
when it is sooner, tied, or starts within FAVORITE_WINDOW after another
viewable launch. A launch you cannot see from home does not take the hero
while a viewable launch or a Starlink train exists, unless the popup is
filtered to that site.
"""
import html
from datetime import datetime, timedelta, timezone

from . import config, launches, sites, sky, trains

FAVORITE_WINDOW = timedelta(minutes=30)
_REGION_NAMES = {"FL": "Florida", "CA": "California", "TX": "Texas"}
TRAIN_FINE_PRINT = (
    "The bright string of pearls only lasts the first few days after launch. "
    "After about a week the satellites spread out, raise their orbits, and dim. "
    "Predictions can drift a minute or two, so go out 5 minutes early. Clouds win every time."
)
_FIST_WORDS = [
    "zero", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven", "twelve",
]


def region_name(code):
    return _REGION_NAMES.get(code or "", "Other")


def fists_count(alt):
    return max(0, int(round(float(alt) / 10.0)))


def fists_phrase(alt):
    count = fists_count(alt)
    if count <= 0:
        return "right on the horizon"
    word = _FIST_WORDS[count] if count < len(_FIST_WORDS) else str(count)
    unit = "fist" if count == 1 else "fists"
    return f"{word} {unit}"


def look_line(direction, alt):
    phrase = fists_phrase(alt)
    if phrase == "right on the horizon":
        return f"Look: {direction}, right on the horizon"
    return f"Look: {direction}, {phrase} up"


def _epoch(dt):
    return int(dt.timestamp())


def _local(dt):
    return dt.astimezone(config.TZ)


def _clock(dt, time_set=True):
    if not time_set:
        return "time not set"
    local = _local(dt)
    return local.strftime("%-I:%M %p").lstrip() + f" {config.TZ_LABEL}"


def _day(dt):
    return _local(dt).strftime("%A")


def _date_label(dt):
    return _local(dt).strftime("%a %b %-d")


def _month_day(dt):
    return _local(dt).strftime("%b %-d")


def when_short(dt, now=None, time_set=True):
    """Compact label for empty states, e.g. 'Mon 6:30 AM'."""
    now = now or datetime.now(timezone.utc)
    local = _local(dt)
    if not time_set:
        return local.strftime("%b %-d")
    days = (local.date() - _local(now).date()).days
    if days <= 6:
        return local.strftime("%a %-I:%M %p").replace("  ", " ")
    return local.strftime("%a %b %-d %-I:%M %p")


def _az(record, az_key, dir_key):
    if record.get(az_key) is not None:
        return float(record[az_key])
    letter = record.get(dir_key) or "N"
    try:
        return sky.COMPASS.index(letter) * 22.5
    except ValueError:
        return 0.0


def _look_alt(pass_):
    if pass_.get("emerges") or float(pass_.get("start_alt") or 0) >= 12:
        return float(pass_["start_alt"])
    return float(pass_["peak_alt"])


def _look_az(pass_):
    if pass_.get("emerges") or float(pass_.get("start_alt") or 0) >= 12:
        return _az(pass_, "start_az", "start_dir")
    return _az(pass_, "peak_az", "peak_dir")


def launch_card(launch, favorite_ids, now=None):
    now = now or datetime.now(timezone.utc)
    if launch.get("site_id") and launch.get("where"):
        site = {
            "id": launch["site_id"],
            "name": launch.get("site_name") or launch["where"],
            "short": launch.get("site_short") or launch.get("site_name") or launch["where"],
            "chip": launch.get("chip") or launch.get("site_name") or launch.get("site_short") or launch["where"],
            "region": launch.get("site") or launch.get("region") or "??",
            "where": launch["where"],
        }
    else:
        site = sites.site_for(launch.get("pad", ""), launch.get("location", ""))
    info = launches.details(launch)
    time_set = launches.time_is_set(launch.get("precision", ""))
    net = launch["net"]
    epoch = _epoch(net)
    florida = site["region"] == "FL"
    place = region_name(site["region"])
    city_id = launch.get("city_id") or sites.city_id_for(site["id"], site.get("name", ""), site.get("region", ""))
    city = launch.get("city_name") or sites.city_name(city_id)
    pad_label = site["short"] if _pad_code(site.get("short")) else ""
    return {
        "uid": f"launch:{site['id']}:{epoch}",
        "kind": "launch",
        "name": launch["mission"],
        "mission": launch["mission"],
        "rocket": launch["rocket"],
        "epoch": epoch,
        "end_epoch": epoch,
        "day": _day(net),
        "clock": _clock(net, time_set),
        "date_label": _date_label(net),
        "month_day": _month_day(net),
        "when_short": when_short(net, now, time_set),
        "time_set": time_set,
        "precision": launch.get("precision") or "",
        "countdown": launches.countdown(net, now),
        "pad": launch.get("pad") or "",
        "location": launch.get("location") or "",
        "site_id": site["id"],
        "site_name": site["name"],
        "site_short": site["short"],
        "chip": site["chip"],
        "where": site["where"],
        "region": site["region"],
        "region_name": place,
        "city_id": city_id,
        "city_name": city,
        "pad_label": pad_label,
        "florida": florida,
        "favorite": city_id in favorite_ids or site["id"] in favorite_ids,
        "visible": bool(info["visible"]),
        "visibility_tag": info["tag"],
        "visibility": info["sentence"],
        "can_we_see": info["can_we_see"],
        "look_dir": info["look_dir"],
        "look_words": info["look_words"],
        "look_az": info.get("look_az") or 0,
        "miles": info["miles"],
        "status": launch.get("status") or "",
        "probability": launch.get("probability"),
        "webcast": launch.get("webcast") or "https://www.spacex.com/launches/",
        "kicker": f"{place.upper()} LAUNCH" if site["region"] in _REGION_NAMES else "LAUNCH",
        "start_az": info.get("look_az") or 0,
        "end_az": info.get("look_az") or 0,
        "peak_alt": 0,
        "note": "",
    }


def _duration(pass_):
    minutes, seconds = divmod(int(pass_["one_sat_seconds"]), 60)
    text = f"{minutes}m {seconds:02d}s each"
    if pass_["count"] > 1:
        text += f" · train ~{pass_['train_minutes']:.0f} min · {pass_['count']} satellites"
    return text


def _train_note(pass_):
    bits = [trains.brightness_note(pass_["age_at_pass"])]
    if pass_.get("fades"):
        bits.append("They fade out as they fly into Earth's shadow.")
    elif pass_.get("emerges"):
        bits.append("They switch on out of Earth's shadow, not at the horizon.")
    if pass_["count"] > 1 and pass_["train_minutes"] > 15:
        bits.append("Spread out: one every minute or two, not a tight line.")
    return " ".join(bits)


def train_card(pass_, now=None):
    now = now or datetime.now(timezone.utc)
    start = pass_["start"]
    alt = _look_alt(pass_)
    direction = pass_.get("start_dir") or "N"
    epoch = _epoch(start)
    return {
        "uid": f"train:{pass_['group']}:{epoch}",
        "kind": "train",
        "name": "Starlink train",
        "mission": "Starlink train",
        "group": pass_["group"],
        "epoch": epoch,
        "end_epoch": _epoch(pass_["end"]),
        "day": _day(start),
        "clock": _clock(start),
        "date_label": _date_label(start),
        "month_day": _month_day(start),
        "when_short": when_short(start, now),
        "time_set": True,
        "countdown": launches.countdown(start, now),
        "where": look_line(direction, alt),
        "look_dir": direction,
        "look_words": sky.COMPASS_WORDS.get(direction, direction.lower()),
        "look_fists": fists_phrase(alt),
        "look_alt": round(alt),
        "start_dir": pass_.get("start_dir") or "",
        "end_dir": pass_.get("end_dir") or "",
        "peak_dir": pass_.get("peak_dir") or "",
        "start_az": _az(pass_, "start_az", "start_dir"),
        "end_az": _az(pass_, "end_az", "end_dir"),
        "peak_az": _az(pass_, "peak_az", "peak_dir"),
        "look_az": _look_az(pass_),
        "start_alt": round(float(pass_.get("start_alt") or 0)),
        "end_alt": round(float(pass_.get("end_alt") or 0)),
        "peak_alt": round(float(pass_.get("peak_alt") or 0)),
        "peak_fists": fists_phrase(pass_["peak_alt"]),
        "duration": _duration(pass_),
        "count": pass_["count"],
        "group_size": pass_.get("group_size") or pass_["count"],
        "age_at_pass": pass_["age_at_pass"],
        "when_tag": trains.when_tag(pass_).replace("⭐ ", "").replace("🌙 ", "").replace("🌅 ", ""),
        "kid_line": trains.kid_line(pass_),
        "note": _train_note(pass_),
        "fades": bool(pass_.get("fades")),
        "emerges": bool(pass_.get("emerges")),
        "kicker": "STARLINK TRAIN",
        "favorite": False,
        "visible": True,
        "florida": False,
        "site_id": "",
        "can_we_see": look_line(direction, alt),
    }


def select_hero(launch_cards, train_cards, filt, now_epoch, window_s=None):
    """Return the hero card, or None.

    `filt` is "all", "favorites", or a city id. Trains compete on All and
    Favorites. A city chip features that place even when a train is sooner.
    """
    if window_s is None:
        window_s = int(FAVORITE_WINDOW.total_seconds())
    filt = filt or sites.FILTER_ALL
    upcoming = [card for card in launch_cards if card["epoch"] > now_epoch - 3600]
    sky_trains = [card for card in train_cards if card["end_epoch"] > now_epoch]
    upcoming.sort(key=lambda card: card["epoch"])
    sky_trains.sort(key=lambda card: card["epoch"])

    if filt == sites.FILTER_FAVORITES:
        upcoming = [card for card in upcoming if card.get("favorite")]
    elif filt != sites.FILTER_ALL:
        upcoming = [card for card in upcoming if _same_place(card, filt)]
        sky_trains = []

    viewable = [card for card in upcoming if card.get("visible")]
    favorite_viewable = [card for card in viewable if card.get("favorite")]
    hero_launch = None
    if filt not in (sites.FILTER_ALL, sites.FILTER_FAVORITES):
        hero_launch = upcoming[0] if upcoming else None
    elif favorite_viewable:
        soonest = viewable[0]
        favorite = favorite_viewable[0]
        if favorite["epoch"] <= soonest["epoch"] + window_s:
            hero_launch = favorite
        else:
            hero_launch = soonest
    elif viewable:
        hero_launch = viewable[0]
    elif filt == sites.FILTER_FAVORITES and upcoming:
        hero_launch = upcoming[0]
    elif upcoming and not sky_trains:
        favorites = [card for card in upcoming if card.get("favorite")]
        hero_launch = (favorites or upcoming)[0]

    hero_train = sky_trains[0] if sky_trains else None
    if hero_launch and hero_train:
        if hero_train["epoch"] <= hero_launch["epoch"]:
            return hero_train
        return hero_launch
    return hero_launch or hero_train


def _tonight_end(now):
    local = _local(now)
    end = local.replace(hour=8, minute=0, second=0, microsecond=0)
    if local >= end:
        end += timedelta(days=1)
    return end


def tonight_train(train_cards, now):
    """Soonest pass that starts before 8 AM tomorrow (the bar's star)."""
    end_epoch = _epoch(_tonight_end(now))
    now_epoch = _epoch(now)
    # A pass already up still counts until it ends, as long as it started before morning.
    coming = [card for card in train_cards if card["end_epoch"] > now_epoch and card["epoch"] < end_epoch]
    coming.sort(key=lambda card: card["epoch"])
    return coming[0] if coming else None


def _same_place(card, filt):
    return card.get("site_id") == filt or card.get("city_id") == filt


def _matching_launches(cards, filt):
    if filt == sites.FILTER_FAVORITES:
        return [card for card in cards if card.get("favorite")]
    if filt != sites.FILTER_ALL:
        return [card for card in cards if _same_place(card, filt)]
    return list(cards)


def _chips(launch_cards, favorite_ids, visible_ids=None):
    """All / Favorites. City cards are the rest of the filter."""
    del launch_cards, visible_ids
    chips = [{"id": "all", "label": "All"}]
    if favorite_ids:
        chips.append({"id": "favorites", "label": "Favorites"})
    return chips


def _empty_trains(florida):
    if florida:
        return f"No trains this week — next Florida launch {florida['when_short']}"
    return "No trains this week"


def _empty_launches(filt, chips):
    del chips
    if filt == sites.FILTER_FAVORITES:
        return "No launches from your favorite cities."
    if filt != sites.FILTER_ALL:
        return f"No upcoming launches from {sites.city_name(filt)}."
    return "No upcoming launches."


def _empty_hero(filt, chips, florida):
    if filt not in (sites.FILTER_ALL, sites.FILTER_FAVORITES):
        return _empty_launches(filt, chips)
    if florida:
        return f"Nothing to walk out for yet — next Florida launch {florida['when_short']}"
    return "Nothing coming up in the next few days."


def place_label(card):
    """Short city and pad for the bar, e.g. 'Cape · SLC-40'."""
    if not card:
        return ""
    pad = (card.get("pad_label") or card.get("site_short") or "").strip()
    city = (card.get("city_name") or "").split(" ")[0]
    if city and pad and city.lower() not in pad.lower():
        return f"{city} · {pad}"
    return pad or city or card.get("region") or ""


def florida_label(florida):
    """Bar label with the city and the pad, e.g. 'Cape · SLC-40'."""
    return place_label(florida) or "FL"


def bar_when(card, now):
    """Countdown, or a calendar date when Launch Library has no clock yet."""
    if not card:
        return ""
    if card.get("time_set") is False:
        return card.get("when_short") or card.get("date_label") or ""
    return launches.countdown(datetime.fromtimestamp(card["epoch"], timezone.utc), now)


def bar_text(hero, florida, tonight, now):
    """Glance line: the hero, then Florida only when that is a different event."""
    del tonight
    parts = []
    if hero and hero.get("kind") == "train":
        clock = _local(datetime.fromtimestamp(hero["epoch"], timezone.utc)).strftime("%-I:%M%p").lower()
        parts.append(f"★ {clock}")
    elif hero and hero.get("kind") == "launch":
        label = place_label(hero) or "Launch"
        when = bar_when(hero, now)
        parts.append(f"🚀 {label} {when}".strip())
    if florida and (not hero or hero.get("uid") != florida.get("uid")):
        if not hero or hero.get("kind") == "train" or not hero.get("florida"):
            label = place_label(florida) or "FL"
            when = bar_when(florida, now)
            parts.append(f"🚀 {label} {when}".strip())
    return "  ".join(parts) if parts else "🚀"


def _when_phrase(countdown):
    if countdown == "now":
        return "up now"
    if not countdown or countdown in ("passed", "date only"):
        return countdown or "coming up"
    return f"in {countdown}"


def bar_tooltip(hero, florida, tonight):
    """Plain-text tooltip. The first lines are what is next and where."""
    lines = []
    if hero:
        lines.append(f"NEXT  {hero['kicker']}")
        lines.append(hero["name"])
        lines.append(f"{hero['day']}  {hero['clock']}  ·  {_when_phrase(hero.get('countdown'))}")
        lines.append(hero["where"])
        if hero["kind"] == "launch" and hero.get("look_dir"):
            lines.append(f"Look {hero['look_dir']}")
        elif hero["kind"] == "launch" and hero.get("can_we_see"):
            lines.append(hero["can_we_see"])
    else:
        lines.append("Nothing coming up")
    if hero and hero["kind"] != "train" and tonight:
        lines.append("")
        lines.append(f"Also  ★ Starlink train  {tonight['clock']}")
        lines.append(tonight["where"])
    if hero and hero["kind"] != "launch" and florida:
        lines.append("")
        lines.append(f"Next Florida launch  {florida['when_short']}")
        lines.append(florida["where"])
    lines.append("")
    lines.append("Click to open the sky board")
    return "\n".join(lines)


def _pad_code(text):
    head, sep, tail = (text or "").partition("-")
    return bool(sep) and head.upper() in {"SLC", "LC", "PAD", "OLP"} and tail.isalnum()


def _site_rows(launch_cards, favorite_ids):
    """One star per city. The detail line names the next pad at that city."""
    rows_src = [dict(city) for city in sites.cities()]
    known = {city["id"] for city in rows_src}
    for card in launch_cards:
        cid = card.get("city_id")
        if cid and cid not in known:
            known.add(cid)
            rows_src.append({
                "id": cid,
                "name": card.get("city_name") or cid,
                "region": card.get("region") or "??",
            })
    rows = []
    for city in rows_src:
        cid = city["id"]
        upcoming = [card for card in launch_cards if card.get("city_id") == cid]
        upcoming.sort(key=lambda card: card["epoch"])
        nxt = upcoming[0] if upcoming else None
        region = city.get("region") or "??"
        pad = ""
        if nxt:
            pad = nxt.get("pad_label") or ""
            if not pad and _pad_code(nxt.get("site_short")):
                pad = nxt["site_short"]
        rows.append({
            "id": cid,
            "name": city.get("name") or cid,
            "short": city.get("name") or cid,
            "label": city.get("name") or cid,
            "detail": pad,
            "region": region,
            "region_name": region_name(region),
            "where": city.get("name") or cid,
            "favorite": cid in favorite_ids,
            "florida": region == "FL",
            "next_mission": nxt["mission"] if nxt else "",
            "next_when": nxt["when_short"] if nxt else "",
            "next_epoch": nxt["epoch"] if nxt else 0,
            "next_time_set": nxt["time_set"] if nxt else True,
        })
    return rows


def _next_florida(launch_cards, now_epoch):
    florida = [card for card in launch_cards if card["florida"] and card["epoch"] > now_epoch - 3600]
    florida.sort(key=lambda card: card["epoch"])
    return florida[0] if florida else None


def _listed_launches(cards, now_epoch, horizon_s=21 * 86400, cap=8):
    """Launches worth a card: dated ones inside three weeks, then a few later."""
    soon = [
        card for card in cards
        if card.get("time_set") and card["epoch"] - now_epoch < horizon_s
    ]
    soon_ids = {id(card) for card in soon}
    later = [card for card in cards if id(card) not in soon_ids]
    return (soon + later[:4])[:cap]


def assemble(raw_launches, raw_passes, cfg, now=None, errors=None):
    now = now or datetime.now(timezone.utc)
    now_epoch = _epoch(now)
    favorite_ids = set(sites.normalize_favorites(cfg.get("favorites") or []))
    launch_cards = []
    for launch in raw_launches:
        if launch["net"] <= now - timedelta(hours=1):
            continue
        try:
            launch_cards.append(launch_card(launch, favorite_ids, now))
        except Exception as exc:  # noqa: BLE001
            errors = list(errors or [])
            errors.append(f"Could not read a launch: {exc}")
    launch_cards.sort(key=lambda card: card["epoch"])
    train_cards = []
    for pass_ in raw_passes:
        if pass_["end"] <= now:
            continue
        try:
            train_cards.append(train_card(pass_, now))
        except Exception as exc:  # noqa: BLE001
            errors = list(errors or [])
            errors.append(f"Could not read a train: {exc}")
    train_cards.sort(key=lambda card: card["epoch"])

    known_ids = {card["site_id"] for card in launch_cards}
    known_ids.update(card.get("city_id") for card in launch_cards if card.get("city_id"))
    known_ids.update(site["id"] for site in sites.catalog())
    known_ids.update(city["id"] for city in sites.cities())
    filt = sites.active_filter(cfg, known_ids)
    if filt == sites.FILTER_FAVORITES and not favorite_ids:
        filt = sites.FILTER_ALL
    filtered = _matching_launches(launch_cards, filt)
    hero = select_hero(launch_cards, train_cards, filt, now_epoch)
    list_launches = _listed_launches(
        [card for card in filtered if not hero or card["uid"] != hero["uid"]], now_epoch)
    listed_trains = [card for card in train_cards if not hero or card["uid"] != hero["uid"]]
    tonight_end = _epoch(_tonight_end(now))
    trains_tonight = [card for card in listed_trains if card["epoch"] < tonight_end][:6]
    trains_later = [card for card in listed_trains if card["epoch"] >= tonight_end][:6]
    list_trains = (trains_tonight + trains_later)[:6]
    florida = _next_florida(launch_cards, now_epoch)
    tonight = tonight_train(train_cards, now)
    visible_ids = {card["site_id"] for card in list_launches}
    if hero and hero.get("kind") == "launch":
        visible_ids.add(hero["site_id"])
    chips = _chips(launch_cards, favorite_ids, visible_ids)
    site_rows = _site_rows(launch_cards, favorite_ids)
    tooltip = bar_tooltip(hero, florida, tonight)
    text = bar_text(hero, florida, tonight, now)
    if hero and hero.get("kind") == "train":
        bar_class = "train"
    elif hero and hero.get("kind") == "launch":
        bar_class = "launch"
    else:
        bar_class = "idle"
    hero_clock = ""
    if hero and hero.get("kind") == "train":
        hero_clock = _local(datetime.fromtimestamp(hero["epoch"], timezone.utc)).strftime("%-I:%M%p").lower()
    return {
        "place": config.PLACE,
        "tz_label": config.TZ_LABEL,
        "generated_epoch": now_epoch,
        "filter": filt,
        "favorites": list(sites.normalize_favorites(cfg.get("favorites") or [])),
        "sites": site_rows,
        "chips": chips,
        "hero": hero,
        "florida": florida,
        "launches": list_launches,
        "trains": list_trains,
        "trains_tonight": trains_tonight,
        "trains_later": trains_later,
        "empty_hero": "" if hero else _empty_hero(filt, chips, florida),
        "empty_launches": "" if list_launches else (
            "That's the one on this list." if hero and hero["kind"] == "launch" else _empty_launches(filt, chips)
        ),
        "empty_trains": "" if list_trains or (hero and hero["kind"] == "train") else _empty_trains(florida),
        "train_fine_print": TRAIN_FINE_PRINT,
        "bar": {
            "text": text,
            "tooltip": tooltip,
            "class": bar_class,
            "star": bool(hero and hero.get("kind") == "train"),
            "train_clock": hero_clock,
            "train_epoch": hero["epoch"] if hero and hero.get("kind") == "train" else 0,
            "train_end_epoch": hero["end_epoch"] if hero and hero.get("kind") == "train" else 0,
            "hero_kind": hero["kind"] if hero else "",
            "hero_florida": bool(hero and hero.get("florida")),
            "hero_uid": hero["uid"] if hero else "",
            "hero_epoch": hero["epoch"] if hero else 0,
            "hero_end_epoch": hero.get("end_epoch", 0) if hero else 0,
            "hero_time_set": True if not hero else hero.get("time_set", True),
            "hero_when": bar_when(hero, now) if hero and hero.get("kind") == "launch" else "",
            "hero_label": place_label(hero) if hero and hero.get("kind") == "launch" else "",
            "florida_epoch": florida["epoch"] if florida else 0,
            "florida_label": florida_label(florida) if florida else "",
            "florida_where": florida["where"] if florida else "",
            "florida_time_set": True if not florida else florida.get("time_set", True),
            "florida_when": bar_when(florida, now) if florida else "",
            "florida_uid": florida["uid"] if florida else "",
        },
        "errors": list(errors or []),
    }


def build(refresh=False, now=None):
    now = now or datetime.now(timezone.utc)
    cfg = sites.load_config()
    errors = []
    raw_launches = []
    raw_passes = []
    try:
        raw_launches = launches.fetch(refresh=refresh)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Launch data unavailable: {exc}")
    try:
        _, raw_passes = trains.compute(refresh=refresh)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Starlink data unavailable: {exc}")
    return assemble(raw_launches, raw_passes, cfg, now, errors)


def waybar_payload(board):
    bar = board["bar"]
    return {
        "text": bar["text"],
        "tooltip": html.escape(bar["tooltip"], quote=False),
        "class": bar["class"],
        "alt": bar["class"],
    }


def empty_board(message):
    now = datetime.now(timezone.utc)
    cfg = sites.default_config()
    board = assemble([], [], cfg, now, [message])
    board["empty_hero"] = message
    return board
