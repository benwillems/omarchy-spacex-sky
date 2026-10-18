"""Shared astronomy helpers (Skyfield)."""
import math
from functools import lru_cache

from skyfield.api import Loader, wgs84

from . import config

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
COMPASS_WORDS = {
    "N": "north", "NNE": "north-northeast", "NE": "northeast", "ENE": "east-northeast",
    "E": "east", "ESE": "east-southeast", "SE": "southeast", "SSE": "south-southeast",
    "S": "south", "SSW": "south-southwest", "SW": "southwest", "WSW": "west-southwest",
    "W": "west", "WNW": "west-northwest", "NW": "northwest", "NNW": "north-northwest",
}


def compass(az_deg):
    return COMPASS[int((az_deg % 360) / 22.5 + 0.5) % 16]


@lru_cache(maxsize=1)
def loader():
    return Loader(str(config.CACHE_DIR))


@lru_cache(maxsize=1)
def timescale():
    return loader().timescale()


@lru_cache(maxsize=1)
def ephemeris():
    # ~17 MB, downloaded once into ~/.cache/spacex-sky
    return loader()("de421.bsp")


def observer():
    return wgs84.latlon(config.LAT, config.LON, elevation_m=config.ELEV_M)


def sun_altitude(t):
    """Sun altitude (deg) at the observer for Skyfield time(s) t."""
    eph = ephemeris()
    obs = eph["earth"] + observer()
    alt, _, _ = obs.at(t).observe(eph["sun"]).apparent().altaz()
    return alt.degrees


def bearing_and_miles(lat1, lon1, lat2, lon2):
    """Great-circle initial bearing (deg) and distance (miles)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    brg = (math.degrees(math.atan2(x, y)) + 360) % 360
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    miles = 3958.8 * 2 * math.asin(math.sqrt(a))
    return brg, miles
