from copy import deepcopy
import unittest

import balancer_core as c


def roster():
    s = c.new_state()
    c.apply_bulk(s, "あお:2000,みどり:2000,休憩さん:2000")
    s["roster"][2]["active"] = False
    return s


def result(state, winner="A"):
    m = c.create_match(state)
    c.record_result(state, m["id"], winner)
    return m


class PrivateTests(unittest.TestCase):
    def test_only_valid_first_assignment_starts_private(self):
        s = c.new_state()
        self.assertIsNone(c.current_private(s))
        c.apply_bulk(s, "あお:2000")
        before = deepcopy(s)
        with self.assertRaises(ValueError): c.create_match(s)
        self.assertEqual(s, before)
        c.apply_bulk(s, "あお:2000,みどり:2000")
        self.assertIsNone(c.current_private(s))
        m = c.create_match(s)
        p = c.current_private(s)
        self.assertEqual((len(s["private_sessions"]), p["number"]), (1, 1))
        self.assertEqual(m["private_id"], p["id"])
        self.assertEqual(set(p["members"]), {"あお", "みどり"})
        c.record_result(s, m["id"], "A")
        c.create_match(s)
        self.assertEqual(len(s["private_sessions"]), 1)

    def test_end_resets_only_live_rests_and_preserves_lifetime_and_session_table(self):
        s = roster()
        result(s)
        result(s, "B")
        before_profiles = deepcopy(s["profiles"])
        before_members = deepcopy(c.current_private(s)["members"])
        c.end_private(s)
        self.assertIsNone(c.current_private(s))
        self.assertIsNotNone(s["private_sessions"][0]["ended_at"])
        self.assertEqual(s["private_sessions"][0]["members"], before_members)
        self.assertEqual(before_members["休憩さん"]["rests"], 2)
        for name, p in s["profiles"].items():
            self.assertEqual(p["rests"], 0)
            expected = dict(before_profiles[name], rests=0)
            self.assertEqual(p, expected)
        ended = deepcopy(s)
        with self.assertRaises(ValueError): c.end_private(s)
        self.assertEqual(s, ended)
        self.assertEqual(c.import_state(c.export_state(s)), s)

    def test_new_private_does_not_start_until_next_assignment_or_include_old_people(self):
        s = roster()
        result(s)
        c.end_private(s)
        completed = deepcopy(s["private_sessions"][0])
        c.reset_roster(s)
        c.apply_bulk(s, "あお:2060,新しい人:1800")
        self.assertIsNone(c.current_private(s))
        self.assertEqual(len(s["private_sessions"]), 1)
        m = result(s)
        p = c.current_private(s)
        self.assertEqual(p["number"], 2)
        self.assertEqual(set(p["members"]), {"あお", "新しい人"})
        self.assertEqual(p["members"]["あお"]["matches"], 1)
        self.assertEqual(s["profiles"]["あお"]["matches"], 2)
        self.assertEqual(s["private_sessions"][0], completed)
        self.assertEqual(m["private_id"], p["id"])
        self.assertEqual(c.import_state(c.export_state(s)), s)

    def test_mid_private_arrivals_and_departures_remain_in_member_table(self):
        s = roster()
        s["profiles"]["歴代だけの人"] = c.profile("歴代だけの人", 1500)
        result(s)
        # Departing players keep their rows, late arrivals start from zero for this private.
        s["roster"][1] = {"name": "途中参加", "rate": "1800", "active": True}
        c.commit_roster(s)
        self.assertEqual(c.current_private(s)["members"]["途中参加"]["matches"], 0)
        result(s)
        members = c.current_private(s)["members"]
        self.assertEqual(members["みどり"]["matches"], 1)
        self.assertEqual(members["途中参加"]["matches"], 1)
        self.assertNotIn("歴代だけの人", members)
        c.end_private(s)
        self.assertEqual(len(s["private_sessions"][0]["members"]), 4)

    def test_pending_blocks_end_and_cancelled_match_has_no_false_stats(self):
        s = roster()
        m = c.create_match(s)
        before = deepcopy(s)
        with self.assertRaises(ValueError): c.end_private(s)
        self.assertEqual(s, before)
        c.cancel_match(s, m["id"])
        c.end_private(s)
        members = s["private_sessions"][0]["members"]
        self.assertTrue(all(p["matches"] == p["rests"] == 0 for p in members.values()))

    def test_result_correction_updates_both_scopes_once_and_cannot_reopen_after_end(self):
        s = roster()
        m = c.create_match(s)
        before = deepcopy(c.current_private(s)["members"])
        c.record_result(s, m["id"], "A")
        recorded = deepcopy(s)
        with self.assertRaises(ValueError): c.record_result(s, m["id"], "A")
        self.assertEqual(s, recorded)
        c.reopen_last_result(s)
        self.assertEqual(c.current_private(s)["members"], before)
        c.record_result(s, m["id"], "B")
        self.assertEqual(c.current_private(s)["members"]["休憩さん"]["rests"], 1)
        c.end_private(s)
        ended = deepcopy(s)
        with self.assertRaises(ValueError): c.reopen_last_result(s)
        self.assertEqual(s, ended)
        result(s)
        c.reopen_last_result(s)
        self.assertEqual(s["private_sessions"][0], ended["private_sessions"][0])

    def test_management_changes_current_members_but_not_finished_snapshots(self):
        s = roster()
        result(s)
        before = deepcopy(c.current_private(s)["members"])
        c.merge_profiles(s, "あお", "みどり")
        merged = c.current_private(s)["members"]["みどり"]
        self.assertEqual(merged["matches"], before["あお"]["matches"] + before["みどり"]["matches"])
        c.undo_profile_management(s)
        self.assertEqual(c.current_private(s)["members"], before)
        values = dict(s["profiles"]["あお"], name="あお正式名", wins=10, losses=4, streak=0, rate="2500")
        c.edit_profile(s, "あお", values)
        member = c.current_private(s)["members"]["あお正式名"]
        self.assertEqual(member["matches"], 1)  # Lifetime edits never become this private's wins.
        self.assertEqual(member["rate"], 2500)
        self.assertNotIn("あお", c.current_private(s)["members"])
        c.delete_profile(s, "休憩さん")
        self.assertIn("休憩さん", c.current_private(s)["members"])
        c.end_private(s)
        completed = deepcopy(s["private_sessions"][0])
        c.merge_profiles(s, "あお正式名", "みどり")
        self.assertEqual(s["private_sessions"][0], completed)
        self.assertEqual(c.import_state(c.export_state(s)), s)

    def test_current_private_and_pending_survive_browser_backup_restore(self):
        s = roster()
        result(s)
        m = c.create_match(s)
        restored = c.import_state(c.export_state(s))
        self.assertEqual(restored, s)
        c.record_result(restored, m["id"], "B")
        self.assertEqual(c.current_private(restored)["members"]["休憩さん"]["rests"], 2)

    def test_legacy_completed_history_remains_unclassified_and_lifetime_preserved(self):
        s = roster()
        result(s)
        s.pop("private_sessions")
        for m in s["history"]:
            m.pop("private_id")
            m.pop("private_members_before")
        profiles = deepcopy(s["profiles"])
        old_history = deepcopy(s["history"])
        restored = c.import_state(c.export_state(s))
        self.assertEqual(restored["private_sessions"], [])
        self.assertEqual(restored["profiles"], profiles)
        self.assertEqual(restored["history"], old_history)
        result(restored)
        self.assertEqual(restored["profiles"]["あお"]["matches"], 2)
        self.assertEqual(c.current_private(restored)["members"]["あお"]["matches"], 1)

    def test_legacy_pending_is_adopted_without_counting_past_matches(self):
        s = roster()
        result(s)
        m = c.create_match(s)
        s.pop("private_sessions")
        for match in s["history"]:
            match.pop("private_id")
            match.pop("private_members_before", None)
        restored = c.import_state(c.export_state(s))
        self.assertEqual(len(restored["private_sessions"]), 1)
        self.assertEqual(c.current_private(restored)["started_at"], m["created_at"])
        self.assertTrue(all(p["matches"] == 0 for p in c.current_private(restored)["members"].values()))
        c.record_result(restored, m["id"], "A")
        self.assertEqual(restored["profiles"]["あお"]["matches"], 2)
        self.assertEqual(c.current_private(restored)["members"]["休憩さん"]["rests"], 1)
        self.assertEqual(c.import_state(c.export_state(restored)), restored)

    def test_legacy_management_undo_is_still_restorable(self):
        s = roster()
        c.delete_profile(s, "あお")
        s.pop("private_sessions")
        s["profile_management_undo"]["data"].pop("private_sessions")
        restored = c.import_state(c.export_state(s))
        c.undo_profile_management(restored)
        self.assertIn("あお", restored["profiles"])
        self.assertEqual(restored["private_sessions"], [])

    def test_corrupt_private_backups_are_rejected_without_partial_restore(self):
        s = roster()
        result(s)
        for mutate in (
            lambda x: x.update(private_sessions={}),
            lambda x: x["private_sessions"][0].update(number=5),
            lambda x: x["history"][0].update(private_id="missing"),
            lambda x: x["history"][0].pop("private_members_before"),
            lambda x: x["private_sessions"][0]["members"]["あお"].update(matches=-1),
        ):
            bad = deepcopy(s)
            mutate(bad)
            with self.assertRaises(ValueError): c.import_state(c.export_state(bad))
        pending = roster()
        c.create_match(pending)
        pending["private_sessions"][0]["ended_at"] = c.now()
        with self.assertRaises(ValueError): c.import_state(c.export_state(pending))


if __name__ == "__main__":
    unittest.main()
