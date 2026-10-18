"""Settings. Defaults are Jacksonville, FL; override with environment variables."""
import os
from pathlib import Path
from zoneinfo import ZoneInfo

LAT = float(os.environ.get("SPACEX_SKY_LAT", "30.13"))
LON = float(os.environ.get("SPACEX_SKY_LON", "-81.53"))
ELEV_M = float(os.environ.get("SPACEX_SKY_ELEV_M", "10"))
PLACE = os.environ.get("SPACEX_SKY_PLACE", "Jacksonville")
TZ = ZoneInfo(os.environ.get("SPACEX_SKY_TZ", "America/New_York"))
TZ_LABEL = os.environ.get("SPACEX_SKY_TZ_LABEL", "ET")

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "spacex-sky"

# Launch Library 2. The free tier allows ~15 requests/hour, so we make ONE
# request (SpaceX only, upcoming) and cache it for an hour.
LL2_BASE = os.environ.get("SPACEX_SKY_LL2", "https://ll.thespacedevs.com/2.3.0")
LAUNCH_CACHE_SECONDS = 60 * 60

# CelesTrak updates GP data every ~2 hours and asks clients not to poll faster.
CELESTRAK_GP = "https://celestrak.org/NORAD/elements/gp.php?GROUP=last-30-days&FORMAT=json"
CELESTRAK_SATCAT = "https://celestrak.org/satcat/records.php?GROUP=last-30-days&FORMAT=json"
GP_CACHE_SECONDS = 2 * 60 * 60
PASS_CACHE_SECONDS = 60 * 60

USER_AGENT = "omarchy-spacex-sky/0.1 (personal desktop widget)"
