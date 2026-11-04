"""Hero selection, site identity, favorites, and the bar tooltip."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from spacex_sky import cli, present, sites


def launch(epoch, site_id, visible=True, favorite=False):
    return {
        "epoch": epoch,
        "end_epoch": epoch,
        "visible": visible,
        "favorite": favorite,
        "site_id": site_id,
        "kind": "launch",
        "uid": f"launch:{site_id}:{epoch}",
    }


def train(epoch, end=None):
    return {
        "epoch": epoch,
        "end_epoch": end if end is not None else epoch + 600,
        "visible": True,
        "favorite": False,
        "site_id": "",
        "kind": "train",
        "uid": f"train:{epoch}",
    }


class HeroTests(unittest.TestCase):
    def test_sooner_train_beats_later_favorite_launch(self):
        hero = present.select_hero(
            [launch(5_000, "slc-40", favorite=True)],
            [train(1_000)],
            "all",
            now_epoch=0,
        )
        self.assertEqual(hero["kind"], "train")

    def test_sooner_viewable_launch_beats_a_much_later_favorite(self):
        hero = present.select_hero(
            [
                launch(1_000, "lc-39a", favorite=False),
                launch(10_000, "slc-40", favorite=True),
            ],
            [],
            "all",
            now_epoch=0,
        )
        self.assertEqual(hero["site_id"], "lc-39a")

    def test_favorite_wins_inside_the_preference_window(self):
        hero = present.select_hero(
            [
                launch(1_000, "lc-39a", favorite=False),
                launch(1_000 + 20 * 60, "slc-40", favorite=True),
            ],
            [],
            "all",
            now_epoch=0,
        )
        self.assertEqual(hero["site_id"], "slc-40")

    def test_unseeable_launch_does_not_beat_a_later_viewable_one(self):
        hero = present.select_hero(
            [
                launch(1_000, "vandenberg", visible=False, favorite=True),
                launch(9_000, "slc-40", visible=True, favorite=True),
            ],
            [],
            "all",
            now_epoch=0,
        )
        self.assertEqual(hero["site_id"], "slc-40")

    def test_train_beats_an_earlier_unseeable_launch(self):
        hero = present.select_hero(
            [launch(1_000, "vandenberg", visible=False)],
            [train(5_000)],
            "all",
            now_epoch=0,
        )
        self.assertEqual(hero["kind"], "train")

    def test_site_filter_features_that_pad(self):
        hero = present.select_hero(
            [
                launch(1_000, "slc-40", favorite=True),
                launch(8_000, "vandenberg", visible=False),
            ],
            [train(500)],
            "vandenberg",
            now_epoch=0,
        )
        self.assertEqual(hero["site_id"], "vandenberg")

    def test_favorites_filter_keeps_a_train_that_is_sooner(self):
        hero = present.select_hero(
            [
                launch(5_000, "slc-40", favorite=True),
                launch(1_000, "vandenberg", visible=False, favorite=False),
            ],
            [train(2_000)],
            "favorites",
            now_epoch=0,
        )
        self.assertEqual(hero["kind"], "train")

    def test_no_viewable_event_prefers_a_favorite_launch(self):
        hero = present.select_hero(
            [
                launch(1_000, "vandenberg", visible=False, favorite=False),
                launch(4_000, "starbase", visible=False, favorite=True),
            ],
            [],
            "all",
            now_epoch=0,
        )
        self.assertEqual(hero["site_id"], "starbase")

    def test_empty(self):
        self.assertIsNone(present.select_hero([], [], "all", 0))


class SiteTests(unittest.TestCase):
    def test_known_pads(self):
        cape = sites.site_for("Space Launch Complex 40", "Cape Canaveral SFS, FL, USA")
        ksc = sites.site_for("Launch Complex 39A", "Kennedy Space Center, FL, USA")
        vand = sites.site_for("Space Launch Complex 4E", "Vandenberg SFB, CA, USA")
        base = sites.site_for("Orbital Launch Pad 2", "SpaceX Starbase, TX, USA")
        self.assertEqual(cape["id"], "slc-40")
        self.assertEqual(cape["where"], "Cape Canaveral SLC-40, FL")
        self.assertEqual(ksc["id"], "lc-39a")
        self.assertEqual(ksc["where"], "KSC LC-39A, FL")
        self.assertEqual(vand["id"], "vandenberg")
        self.assertEqual(vand["where"], "Vandenberg SLC-4E, CA")
        self.assertEqual(base["id"], "starbase")
        self.assertEqual(base["where"], "Starbase TX")

    def test_resolve_names(self):
        known = sites.catalog()
        self.assertEqual(sites.resolve_site_ids("SLC-40", known), ["slc-40"])
        self.assertEqual(sites.resolve_site_ids("KSC LC-39A", known), ["lc-39a"])
        self.assertEqual(sites.resolve_site_ids("Vandenberg", known), ["vandenberg"])
        self.assertEqual(sites.resolve_site_ids("Starbase TX", known), ["starbase"])
        self.assertEqual(sites.resolve_site_ids("florida", known), ["slc-40", "lc-39a", "lc-39b"])

    def test_cape_pads_share_a_city(self):
        self.assertEqual(sites.city_id_for("slc-40", "Cape Canaveral SLC-40", "FL"), "cape-canaveral")
        self.assertEqual(sites.city_id_for("slc-41", "Cape Canaveral SLC-41", "FL"), "cape-canaveral")
        self.assertEqual(sites.city_id_for("cape-canaveral", "Cape Canaveral", "FL"), "cape-canaveral")
        self.assertEqual(sites.city_id_for("lc-39a", "KSC LC-39A", "FL"), "kennedy")
        self.assertEqual(sites.city_id_for("lc-39b", "KSC LC-39B", "FL"), "kennedy")
        self.assertEqual(sites.city_id_for("slc-4e", "Vandenberg SLC-4E", "CA"), "vandenberg")
        self.assertEqual(
            sites.normalize_favorites(["slc-40", "lc-39a", "lc-39b", "cape-canaveral"]),
            ["cape-canaveral", "kennedy"],
        )
        self.assertEqual(sites.favorite_target("Cape Canaveral"), "cape-canaveral")
        self.assertEqual(sites.favorite_target("SLC-40"), "cape-canaveral")
        self.assertEqual(sites.favorite_target("LC-39A"), "kennedy")

    def test_ambiguous_site_is_an_error(self):
        known = sites.catalog()
        with self.assertRaises(ValueError):
            sites.resolve_site_ids("lc-39", known)


class TextTests(unittest.TestCase):
    def test_fists_and_look_line(self):
        self.assertEqual(present.fists_phrase(34), "three fists")
        self.assertEqual(present.fists_phrase(10), "one fist")
        self.assertEqual(present.look_line("SSE", 20), "Look: SSE, two fists up")
        self.assertEqual(present.look_line("E", 4), "Look: E, right on the horizon")

    def test_tooltip_leads_with_next_and_where(self):
        hero = {
            "kind": "train",
            "kicker": "STARLINK TRAIN",
            "name": "Starlink train",
            "day": "Sunday",
            "clock": "6:02 AM ET",
            "countdown": "5h 12m",
            "where": "Look: ESE, three fists up",
            "look_dir": "ESE",
        }
        florida = {"when_short": "Mon 6:30 AM", "where": "Cape Canaveral SLC-40, FL"}
        tip = present.bar_tooltip(hero, florida, None)
        self.assertTrue(tip.startswith("NEXT  STARLINK TRAIN"))
        self.assertIn("Look: ESE, three fists up", tip.splitlines()[:4])
        self.assertIn("Cape Canaveral SLC-40, FL", tip)


def _raw(epoch, site_id, mission):
    site = next(item for item in sites.catalog() if item["id"] == site_id)
    net = datetime.fromtimestamp(epoch, timezone.utc)
    return {
        "mission": mission,
        "name": mission,
        "rocket": "Falcon 9",
        "net": net,
        "precision": "Minute",
        "status": "Go",
        "pad": site["short"],
        "location": site["where"],
        "site": site["region"],
        "site_id": site["id"],
        "site_name": site["name"],
        "site_short": site["short"],
        "chip": site["chip"],
        "where": site["where"],
        "lat": None,
        "lon": None,
        "probability": None,
    }


class BoardTests(unittest.TestCase):
    def test_cities_share_a_star_and_the_bar_names_the_pad(self):
        now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
        raw = [
            _raw(int((now + timedelta(days=3)).timestamp()), "vandenberg", "West Coast"),
            _raw(int((now + timedelta(days=1)).timestamp()), "slc-40", "Bandwagon"),
            _raw(int((now + timedelta(days=2)).timestamp()), "lc-39a", "Crew"),
        ]
        details = {
            "visible": False,
            "tag": "no",
            "sentence": "Not visible.",
            "can_we_see": "No.",
            "look_dir": "",
            "look_words": "",
            "miles": None,
        }
        with patch("spacex_sky.present.launches.details", return_value=details):
            board = present.assemble(raw, [], {"favorites": ["lc-39a"], "filter": "all"}, now)
        ids = [row["id"] for row in board["sites"]]
        self.assertEqual(ids, ["cape-canaveral", "kennedy", "vandenberg", "starbase"])
        by_id = {row["id"]: row for row in board["sites"]}
        self.assertFalse(by_id["cape-canaveral"]["favorite"])
        self.assertTrue(by_id["kennedy"]["favorite"])
        self.assertEqual(by_id["cape-canaveral"]["region_name"], "Florida")
        self.assertEqual(by_id["cape-canaveral"]["label"], "Cape Canaveral")
        self.assertEqual(by_id["cape-canaveral"]["detail"], "SLC-40")
        self.assertEqual(by_id["kennedy"]["label"], "Kennedy")
        self.assertEqual(by_id["kennedy"]["detail"], "LC-39A")
        self.assertEqual(by_id["cape-canaveral"]["next_mission"], "Bandwagon")
        self.assertEqual(by_id["starbase"]["next_when"], "")
        self.assertEqual(by_id["vandenberg"]["region_name"], "California")
        self.assertEqual(by_id["vandenberg"]["label"], "Vandenberg")
        self.assertEqual(by_id["vandenberg"]["detail"], "")
        self.assertEqual(board["favorites"], ["kennedy"])
        shown = list(board["launches"])
        if board["hero"] and board["hero"].get("kind") == "launch":
            shown.append(board["hero"])
        cape = next(card for card in shown if card["site_id"] == "slc-40")
        self.assertEqual(cape["kicker"], "FLORIDA LAUNCH")
        self.assertEqual(cape["where"], "Cape Canaveral SLC-40, FL")
        self.assertEqual(cape["city_id"], "cape-canaveral")
        self.assertEqual(cape["pad_label"], "SLC-40")
        self.assertFalse(cape["favorite"])
        crew = next(card for card in shown if card["site_id"] == "lc-39a")
        self.assertTrue(crew["favorite"])
        self.assertEqual(crew["pad_label"], "LC-39A")
        west = next(card for card in board["launches"] if card["site_id"] == "vandenberg")
        self.assertEqual(west["kicker"], "CALIFORNIA LAUNCH")
        self.assertEqual(west["city_id"], "vandenberg")
        self.assertEqual(board["florida"]["site_short"], "SLC-40")
        self.assertEqual(board["hero"]["month_day"], "Oct 27")
        self.assertEqual(board["hero"]["date_label"], "Tue Oct 27")
        self.assertTrue(board["bar"]["text"].startswith("🚀 Kennedy · LC-39A"))
        self.assertNotIn("Cape · SLC-40", board["bar"]["text"])
        self.assertEqual(board["bar"]["hero_label"], "Kennedy · LC-39A")
        self.assertEqual(board["bar"]["florida_label"], "Cape · SLC-40")
        self.assertTrue(board["bar"]["hero_florida"])
        chip_labels = [chip["label"] for chip in board["chips"]]
        self.assertEqual(chip_labels[0], "All")
        self.assertIn("Favorites", chip_labels)
        self.assertNotIn("Cape Canaveral", chip_labels)
        self.assertNotIn("SLC-40", chip_labels)

    def test_florida_notices_name_the_pad_and_skip_other_states(self):
        now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
        florida = _raw(int((now + timedelta(hours=6)).timestamp()), "slc-40", "Bandwagon")
        soon = _raw(int((now + timedelta(minutes=10)).timestamp()), "lc-39a", "Crew")
        california = _raw(int((now + timedelta(hours=2)).timestamp()), "vandenberg", "West")
        day = cli.florida_notices([florida, california], now, set(), minutes=15)
        self.assertEqual(len(day), 1)
        self.assertIn("Cape Canaveral SLC-40, FL", day[0][1])
        self.assertIn("Bandwagon", day[0][2])
        self.assertTrue(day[0][0].startswith("launch-day:"))
        near = cli.florida_notices([soon, florida], now, {day[0][0]}, minutes=15)
        keys = [item[0] for item in near]
        self.assertTrue(any(key.startswith("launch:Crew") or "lc-39a" in key or key.startswith("launch:") for key in keys))
        self.assertTrue(any("KSC LC-39A, FL" in item[1] and "in 10 min" in item[1] for item in near))
        self.assertFalse(any(item[0] == day[0][0] for item in near))
        self.assertEqual(cli.florida_notices([california], now, set()), [])

    def test_bar_uses_a_date_when_the_clock_is_unknown(self):
        now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
        card = {
            "kind": "launch",
            "uid": "launch:slc-40:1",
            "epoch": int((now + timedelta(days=5)).timestamp()),
            "time_set": False,
            "when_short": "Oct 30",
            "city_name": "Cape Canaveral",
            "pad_label": "SLC-40",
            "florida": True,
        }
        text = present.bar_text(card, card, None, now)
        self.assertIn("Oct 30", text)
        self.assertNotIn("d ", text)

    def test_starred_city_gets_a_launch_notice(self):
        now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
        california = _raw(int((now + timedelta(hours=6)).timestamp()), "vandenberg", "West")
        notices = cli.launch_notices([california], now, set(), minutes=15, favorite_ids=["vandenberg"])
        self.assertEqual(len(notices), 1)
        self.assertIn("Vandenberg", notices[0][1])
        self.assertEqual(cli.launch_notices([california], now, set(), minutes=15, favorite_ids=[]), [])

    def test_empty_favorites_hides_the_favorites_chip(self):
        now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
        raw = [_raw(int((now + timedelta(days=1)).timestamp()), "slc-40", "Bandwagon")]
        details = {
            "visible": False,
            "tag": "no",
            "sentence": "Not visible.",
            "can_we_see": "No.",
            "look_dir": "",
            "look_words": "",
            "miles": None,
        }
        with patch("spacex_sky.present.launches.details", return_value=details):
            board = present.assemble(raw, [], {"favorites": [], "filter": "favorites"}, now)
        labels = [chip["label"] for chip in board["chips"]]
        self.assertEqual(labels, ["All"])
        self.assertEqual(board["filter"], "all")


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        os.environ["SPACEX_SKY_CONFIG"] = str(Path(self._dir.name) / "config.toml")

    def tearDown(self):
        os.environ.pop("SPACEX_SKY_CONFIG", None)
        self._dir.cleanup()

    def test_defaults_and_toggle(self):
        cfg = sites.load_config()
        self.assertEqual(cfg["favorites"], ["cape-canaveral", "kennedy"])
        self.assertEqual(cfg["filter"], "all")
        sid, added, favorites = sites.toggle_favorite("Vandenberg")
        self.assertEqual(sid, "vandenberg")
        self.assertTrue(added)
        self.assertIn("vandenberg", favorites)
        sites.toggle_favorite("slc-40")
        self.assertNotIn("cape-canaveral", sites.load_config()["favorites"])
        self.assertIn("kennedy", sites.load_config()["favorites"])
        self.assertEqual(sites.set_filter("LC-39A"), "kennedy")
        self.assertEqual(sites.load_config()["filter"], "kennedy")
        self.assertEqual(sites.set_filter("favorites"), "favorites")

    def test_pad_favorites_migrate_without_adding_cities(self):
        path = Path(os.environ["SPACEX_SKY_CONFIG"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('favorites = ["lc-39a"]\nfilter = "slc-40"\n')
        cfg = sites.load_config()
        self.assertEqual(cfg["favorites"], ["kennedy"])
        self.assertEqual(cfg["filter"], "cape-canaveral")
        text = path.read_text()
        self.assertIn('"kennedy"', text)
        self.assertNotIn("lc-39a", text)
        self.assertNotIn("cape-canaveral", text.split("filter")[0])
        again = sites.load_config()
        self.assertEqual(again["favorites"], ["kennedy"])
        self.assertEqual(again["filter"], "cape-canaveral")


if __name__ == "__main__":
    unittest.main()
