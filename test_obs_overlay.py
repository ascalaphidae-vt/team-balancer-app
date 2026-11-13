from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import balancer_core as core
import obs_overlay as obs


APP = Path(__file__).with_name("team-balancer-app.py")


class ObsTests(unittest.TestCase):
    def test_feed_owner_timeout_and_stop(self):
        feeds = obs.OverlayFeeds()
        with patch.object(obs, "monotonic", return_value=0) as clock:
            feeds.start("link", "first", "あお")
            self.assertEqual(feeds.read("link"), "あお")
            clock.return_value = obs.FEED_TIMEOUT
            self.assertEqual(feeds.read("link"), "")
            feeds.start("link", "second", "きいろ")
            self.assertFalse(feeds.publish("link", "first", "あか"))
            feeds.stop("link", "first")
            self.assertEqual(feeds.read("link"), "きいろ")
            feeds.stop("link", "second")
            self.assertEqual(feeds.read("link"), "")

    def test_tie_and_literal_display(self):
        match = {"team_a": [{"name": "乙", "rate": 4000}], "team_b": [{"name": "A<&", "rate": 4000}]}
        self.assertEqual(obs.strongest_player(match), "A<&")
        self.assertIn("A&lt;&amp;", obs.overlay_markup("A<&"))
        self.assertNotIn("4000", obs.overlay_markup("A<&"))

    def test_browser_source_updates_for_two_matches_and_hides_after_result_or_stop(self):
        state = core.new_state()
        core.apply_bulk(state, "\n".join(f"P{i}:{1000 + i * 100}" for i in range(8)) + "\n休憩:9999")
        state["roster"][8]["active"] = False
        match = core.create_match(state)
        controller = AppTest.from_file(str(APP))
        controller.session_state.store_token = "test-controller"
        controller.session_state.hydrated = True
        controller.session_state.model = state
        controller.run()
        next(b for b in controller.button if b.label == "OBS連携を開始").click().run()
        key = controller.session_state.obs_key
        self.assertTrue(obs.valid_key(key))

        viewer = AppTest.from_file(str(APP))
        viewer.query_params["obs"] = key
        viewer.run()
        self.assertFalse(viewer.exception)
        self.assertFalse(controller.exception)
        self.assertIn("P7", viewer.get("html")[-1].proto.body)
        self.assertNotIn("1700", viewer.get("html")[-1].proto.body)
        self.assertFalse(viewer.tabs)

        controller.radio(key=f"winner_{match['id']}").set_value("A").run()
        next(b for b in controller.button if b.label == "🏆 この結果を登録する").click().run()
        viewer.run()
        self.assertEqual(viewer.get("html")[-1].proto.body, obs.overlay_markup(""))

        controller.text_input(key="rate_0").set_value("5000").run()
        next(b for b in controller.button if b.label == "✅ チームを分ける").click().run()
        viewer.run()
        self.assertIn("P0", viewer.get("html")[-1].proto.body)
        next(b for b in controller.button if b.label == "OBS連携を停止").click().run()
        viewer.run()
        self.assertEqual(viewer.get("html")[-1].proto.body, obs.overlay_markup(""))
        self.assertFalse(controller.exception)
