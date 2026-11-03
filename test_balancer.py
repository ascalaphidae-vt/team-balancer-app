"""Run with: python -m unittest -v test_balancer test_app"""
from copy import deepcopy
import json
import unittest
import balancer_core as c


def populated(count=10, playing=8):
    s = c.new_state()
    for i in range(count):
        s["roster"][i] = {"name": f"参加者{i}", "rate": str(2000 + i * 100), "active": i < playing}
    return s


class MatchTests(unittest.TestCase):
    def test_result_counts_all_eight_and_two_rests_once(self):
        s = populated()
        m = c.create_match(s)
        c.record_result(s, m["id"], "A")
        winners = {p["name"] for p in m["team_a"]}
        for i in range(10):
            p = s["profiles"][f"参加者{i}"]
            self.assertEqual(p["initial_rate"], 2000 + i * 100)
            self.assertEqual(p["matches"], int(i < 8))
            self.assertEqual(p["rests"], int(i >= 8))
            self.assertEqual(p["wins"], int(p["name"] in winners))
            if i < 8:
                self.assertNotEqual(p["rate"], p["initial_rate"])
        before = deepcopy(s)
        with self.assertRaises(ValueError):
            c.record_result(s, m["id"], "A")
        self.assertEqual(s, before)

    def test_pending_cannot_be_overwritten_or_inputs_committed(self):
        s = populated()
        m = c.create_match(s)
        before = deepcopy(s)
        for fn in (c.create_match, c.commit_roster, c.reset_roster):
            with self.assertRaises(ValueError): fn(s)
        self.assertEqual(s, before)
        restored = c.import_state(c.export_state(s))
        self.assertEqual(c.pending_match(restored)["id"], m["id"])
        c.record_result(restored, m["id"], "B")
        self.assertEqual(sum(p["wins"] for p in restored["profiles"].values()), 4)

    def test_undo_and_correct_winner_restores_ratings_and_rests(self):
        s = populated()
        m = c.create_match(s)
        before = deepcopy(s["profiles"])
        c.record_result(s, m["id"], "A")
        s["profiles"]["後から登録"] = c.profile("後から登録", 1500)
        c.reopen_last_result(s)
        for name, p in before.items(): self.assertEqual(s["profiles"][name], p)
        self.assertIn("後から登録", s["profiles"])
        c.record_result(s, m["id"], "B")
        self.assertEqual(sum(p["matches"] for p in s["profiles"].values()), 8)
        self.assertEqual(sum(p["rests"] for p in s["profiles"].values()), 2)
        self.assertEqual(len(s["history"]), 1)
        self.assertEqual(c.import_state(c.export_state(s)), s)

    def test_cancel_never_counts_matches_or_rests(self):
        s = populated()
        m = c.create_match(s)
        c.cancel_match(s, m["id"])
        self.assertTrue(all(p["matches"] == p["rests"] == 0 for p in s["profiles"].values()))
        self.assertEqual(c.create_match(s)["number"], 2)

    def test_snapshot_not_current_slot_name_controls_result(self):
        s = populated()
        m = c.create_match(s)
        s["roster"][0]["name"] = "別人"
        c.record_result(s, m["id"], "A")
        self.assertEqual(s["profiles"]["参加者0"]["matches"], 1)
        self.assertNotIn("別人", s["profiles"])

    def test_duplicate_or_invalid_bulk_does_not_clear_existing_inputs(self):
        s = populated()
        before = deepcopy(s)
        for text in ("同名:2000,同名:1000", "名前:abc", "形式不正", ",".join(f"a{i}:1" for i in range(11))):
            with self.assertRaises(ValueError): c.apply_bulk(s, text)
            self.assertEqual(s, before)

    def test_invalid_roster_does_not_register_partial_profiles(self):
        for bad in ("abc", "-10", "1000000"):
            s = populated()
            s["roster"][8]["rate"] = bad
            before = deepcopy(s)
            with self.assertRaises(ValueError): c.create_match(s)
            self.assertEqual(s, before)

    def test_fullwidth_and_initial_latest_reload(self):
        s = c.new_state()
        c.apply_bulk(s, "あすふぃだ：２６３０\nイシガケ：２０００")
        m = c.create_match(s)
        c.record_result(s, m["id"], "A")
        latest = s["profiles"]["あすふぃだ"]["rate"]
        c.reset_roster(s)
        c.load_profile(s, "あすふぃだ")
        self.assertEqual(s["roster"][0]["rate"], str(latest))
        c.reset_roster(s)
        c.load_profile(s, "あすふぃだ", use_initial=True)
        self.assertEqual(s["roster"][0]["rate"], "2630")
        self.assertEqual(s["profiles"]["あすふぃだ"]["initial_rate"], 2630)

    def test_inactive_named_player_is_not_an_empty_slot(self):
        s = populated()
        c.commit_roster(s)
        s["profiles"]["新規"] = c.profile("新規", 1000)
        before = deepcopy(s)
        with self.assertRaises(ValueError): c.load_profile(s, "新規")
        self.assertEqual(s, before)

    def test_rating_modes_streak_reset_cap_and_floor(self):
        settings = dict(c.DEFAULT_SETTINGS)
        self.assertEqual([c.calculate_change(2000, True, i, settings) for i in range(1, 7)], [60, 75, 90, 105, 120, 120])
        self.assertEqual(c.calculate_change(2000, False, -3, settings), -90)
        self.assertEqual(c.next_streak(-5, True), 1)
        self.assertEqual(c.next_streak(5, False), -1)
        settings["decrease"] = False
        self.assertEqual(c.calculate_change(2000, False, -3, settings), 0)
        settings["streak_bonus"] = False
        self.assertEqual(c.calculate_change(2000, True, 10, settings), 60)
        settings.update(percent=20.0, decrease=True, streak_bonus=True)
        self.assertEqual(c.calculate_change(1, False, -5, settings), -1)
        self.assertEqual(c.calculate_change(0, True, 1, settings), 1)
        self.assertEqual(c.calculate_change(c.MAX_RATE, True, 1, settings), 0)
        settings["percent"] = 0.0
        self.assertEqual(c.calculate_change(2000, True, 1, settings), 0)

    def test_saved_pending_restored_with_winner_and_undo(self):
        s = populated()
        m = c.create_match(s)
        m["selected_winner"] = "B"
        restored = c.import_state(c.export_state(s))
        self.assertEqual(c.pending_match(restored)["selected_winner"], "B")
        c.record_result(restored, m["id"], "B")
        restored = c.import_state(c.export_state(restored))
        c.reopen_last_result(restored)
        self.assertIsNone(c.pending_match(restored)["selected_winner"])
        self.assertEqual(c.import_state(c.export_state(restored)), restored)

    def test_corrupt_backup_does_not_load(self):
        s = populated()
        m = c.create_match(s)
        c.record_result(s, m["id"], "A")
        for mutate in (
            lambda x: x.update(version=100),
            lambda x: x["settings"].update(percent=-1),
            lambda x: x["history"][0].update(changes=[]),
            lambda x: x["history"][0]["team_a"][0].update(name="存在しない"),
            lambda x: x["profiles"]["参加者0"].update(matches=999),
        ):
            bad = deepcopy(s)
            mutate(bad)
            with self.assertRaises(ValueError): c.import_state(json.dumps(bad, ensure_ascii=False))
        for raw in ("[]", "null", "{", "{\"version\":2}"):
            with self.assertRaises(ValueError): c.import_state(raw)


class ProfileManagementTests(unittest.TestCase):
    def recorded(self):
        s = populated(count=4, playing=2)
        m = c.create_match(s)
        c.record_result(s, m["id"], "A")
        return s

    def roundtrip(self, state):
        restored = c.import_state(c.export_state(state))
        self.assertEqual(restored, state)
        return restored

    def test_merge_sums_counts_selects_rates_collapses_roster_and_keeps_history(self):
        s = self.recorded()
        before = deepcopy(s)
        a, b = deepcopy(s["profiles"]["参加者0"]), deepcopy(s["profiles"]["参加者1"])
        c.merge_profiles(s, "参加者0", "参加者1", initial_from="source", rate_from="target")
        merged = s["profiles"]["参加者1"]
        self.assertNotIn("参加者0", s["profiles"])
        self.assertEqual(merged["matches"], a["matches"] + b["matches"])
        self.assertEqual(merged["wins"], a["wins"] + b["wins"])
        self.assertEqual(merged["losses"], a["losses"] + b["losses"])
        self.assertEqual(merged["initial_rate"], a["initial_rate"])
        self.assertEqual(merged["rate"], b["rate"])
        self.assertEqual(merged["streak"], b["streak"])
        self.assertEqual(s["history"], before["history"])
        self.assertEqual(sum(r["name"] == "参加者1" for r in s["roster"]), 1)
        self.assertEqual(s["profile_links"]["参加者0"], "参加者1")
        self.roundtrip(s)
        with self.assertRaises(ValueError): c.reopen_last_result(s)
        c.undo_profile_management(s)
        self.assertEqual(s["profiles"], before["profiles"])
        self.assertEqual(s["roster"], before["roster"])
        c.reopen_last_result(s)
        self.assertIsNotNone(c.pending_match(s))

    def test_delete_removes_all_current_references_but_preserves_historical_matches(self):
        s = self.recorded()
        history = deepcopy(s["history"])
        c.delete_profile(s, "参加者0")
        self.assertNotIn("参加者0", s["profiles"])
        self.assertFalse(any(r["name"] == "参加者0" for r in s["roster"]))
        self.assertEqual(s["history"], history)
        self.assertIsNone(s["profile_links"]["参加者0"])
        s = self.roundtrip(s)
        before = deepcopy(s)
        with self.assertRaises(ValueError): c.load_profile(s, "参加者0")
        self.assertEqual(s, before)
        c.undo_profile_management(s)
        self.assertIn("参加者0", s["profiles"])

    def test_edit_name_fullwidth_rates_and_statistics_survives_restore(self):
        s = self.recorded()
        values = dict(s["profiles"]["参加者0"], name="改名した人", initial_rate="２５００", rate="２６００",
                      wins=10, losses=4, rests=7, streak=-3)
        c.edit_profile(s, "参加者0", values)
        p = s["profiles"]["改名した人"]
        self.assertEqual((p["initial_rate"], p["rate"], p["matches"]), (2500, 2600, 14))
        self.assertEqual(s["roster"][0]["name"], "改名した人")
        self.assertEqual(s["roster"][0]["rate"], "2600")
        self.assertNotIn("参加者0", s["profiles"])
        self.roundtrip(s)

    def test_invalid_edit_and_merge_are_atomic(self):
        s = self.recorded()
        before = deepcopy(s)
        for change in ({"name": "参加者1"}, {"rate": "abc"}, {"wins": -1}, {"streak": 100}, {"name": ""}):
            values = dict(s["profiles"]["参加者0"], **change)
            with self.assertRaises(ValueError): c.edit_profile(s, "参加者0", values)
            self.assertEqual(s, before)
        for source, target in (("参加者0", "参加者0"), ("未登録", "参加者1")):
            with self.assertRaises(ValueError): c.merge_profiles(s, source, target)
            self.assertEqual(s, before)

    def test_pending_match_blocks_all_management(self):
        s = populated(count=2, playing=2)
        c.create_match(s)
        before = deepcopy(s)
        for fn, args in ((c.delete_profile, ("参加者0",)), (c.merge_profiles, ("参加者0", "参加者1")),
                         (c.edit_profile, ("参加者0", s["profiles"]["参加者0"]))):
            with self.assertRaises(ValueError): fn(s, *args)
            self.assertEqual(s, before)

    def test_new_results_after_management_can_be_corrected_without_resurrection(self):
        s = self.recorded()
        c.delete_profile(s, "参加者0")
        s["roster"][2]["active"] = True
        m = c.create_match(s)
        self.assertNotIn("profile_management_undo", s)
        c.record_result(s, m["id"], "B")
        self.roundtrip(s)
        c.reopen_last_result(s)
        self.assertNotIn("参加者0", s["profiles"])
        c.record_result(s, m["id"], "A")
        self.roundtrip(s)

    def test_chained_merges_then_delete_all_are_valid_and_reversible(self):
        s = self.recorded()
        c.merge_profiles(s, "参加者0", "参加者1")
        c.merge_profiles(s, "参加者1", "参加者2")
        self.assertEqual(s["profile_links"]["参加者0"], "参加者2")
        c.delete_profile(s, "参加者2")
        self.assertIsNone(s["profile_links"]["参加者0"])
        c.delete_profile(s, "参加者3")
        self.assertEqual(s["profiles"], {})
        s = self.roundtrip(s)
        c.undo_profile_management(s)
        self.assertEqual(set(s["profiles"]), {"参加者3"})
        self.roundtrip(s)

    def test_undo_expires_on_next_mutation_and_legacy_backup_still_loads(self):
        s = self.roundtrip(self.recorded())
        c.delete_profile(s, "参加者0")
        c.touch(s)
        with self.assertRaises(ValueError): c.undo_profile_management(s)
        self.roundtrip(s)

    def test_corrupt_management_backup_is_rejected(self):
        s = self.recorded()
        c.delete_profile(s, "参加者0")
        bad = deepcopy(s)
        bad["profile_management_undo"]["data"]["profiles"] = {}
        with self.assertRaises(ValueError): c.import_state(c.export_state(bad))
        bad = deepcopy(s)
        bad["profile_links"]["参加者0"] = "未登録"
        with self.assertRaises(ValueError): c.import_state(c.export_state(bad))
        bad = deepcopy(s)
        bad["result_undo_blocked_through"] = 0
        with self.assertRaises(ValueError): c.import_state(c.export_state(bad))


if __name__ == "__main__":
    unittest.main()
