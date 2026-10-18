"""Tiny JSON-over-HTTP cache. If the network fails we fall back to stale data."""
import json
import sys
import time
import urllib.error
import urllib.request

from . import config


def _path(name):
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return config.CACHE_DIR / name


def read_cache(name, max_age):
    """Return cached data if younger than max_age seconds, else None."""
    p = _path(name)
    if p.exists() and time.time() - p.stat().st_mtime < max_age:
        return json.loads(p.read_text())
    return None


def write_cache(name, data):
    p = _path(name)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(p)


def cache_age(name):
    p = _path(name)
    return time.time() - p.stat().st_mtime if p.exists() else None


def fetch_json(url, name, max_age, refresh=False):
    """Fetch url as JSON, cached under ~/.cache/spacex-sky/<name>."""
    if not refresh:
        cached = read_cache(name, max_age)
        if cached is not None:
            return cached
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        write_cache(name, data)
        return data
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        stale = _path(name)
        if stale.exists():
            age_h = cache_age(name) / 3600
            print(f"(network problem: {e}; using cached data from {age_h:.1f}h ago)", file=sys.stderr)
            return json.loads(stale.read_text())
        raise RuntimeError(f"Could not download {url}: {e}") from e
