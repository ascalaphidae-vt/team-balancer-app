from copy import deepcopy
from itertools import combinations
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

import balancer_core as core


APP = Path(__file__).with_name("team-balancer-app.py")
RATES = [2892, 2339, 2316, 3346, 2220, 3009, 3329, 2451]


def players():
    return [{"name": f"P{i}", "rate": rate} for i, rate in enumerate(RATES)]


def prepared():
    state = core.new_state()
    core.apply_bulk(state, "\n".join(f'P{i}:{rate}' for i, rate in enumerate(RATES)))
    return state


def unordered_teams(a, b):
    return {frozenset(p["name"] for p in team) for team in (a, b)}


class AssignmentTests(unittest.TestCase):
    def test_tolerance_is_added_to_best_gap_and_zero_keeps_only_optima(self):
        rows = players()
        a, b, best = core.assign_teams(rows)
        self.assertEqual(best, 74)
        previous = {"team_a": a, "team_b": b}
        for tolerance in (0, 9):
            x, y, diff = core.assign_teams(rows, tolerance, previous)
            self.assertEqual(diff, 74)
            self.assertEqual(unordered_teams(x, y), unordered_teams(a, b))
        x, y, diff = core.assign_teams(rows, 25, previous)
        self.assertEqual(diff, 84)
        self.assertNotEqual(unordered_teams(x, y), unordered_teams(a, b))
        mirrored = {"team_a": b, "team_b": a}
        x2, y2, diff2 = core.assign_teams(rows, 25, mirrored)
        self.assertEqual((diff2, unordered_teams(x2, y2)), (diff, unordered_teams(x, y)))
        # Without a previous match there is no reason to increase the gap.
        self.assertEqual(core.assign_teams(rows, 100)[2], 74)

    def test_fixed_first_player_can_be_in_b_and_all_fixed_rates_count(self):
        rows = players()
        fixed = {"P0": "B", "P1": "A", "P3": "A"}
        before = deepcopy(rows)
        a, b, diff = core.assign_teams(rows, fixed_teams=fixed)
        self.assertIn("P0", {p["name"] for p in b})
        self.assertTrue({"P1", "P3"} <= {p["name"] for p in a})
        legal_differences = []
        for indexes in combinations(range(8), 4):
            if 0 not in indexes and 1 in indexes and 3 in indexes:
                legal_differences.append(abs(2 * sum(RATES[i] for i in indexes) - sum(RATES)))
        self.assertEqual(diff, min(legal_differences))
        self.assertEqual(rows, before)

    def test_odd_teams_can_put_three_fixed_players_on_a(self):
        rows = players()[:5]
        fixed = {"P0": "A", "P1": "A", "P2": "A", "P3": "B"}
        a, b, _ = core.assign_teams(rows, fixed_teams=fixed)
        self.assertEqual((len(a), len(b)), (3, 2))

    def test_impossible_fixed_teams_leave_state_unchanged(self):
        state = prepared()
        state["team_fixing_enabled"] = True
        for row in state["roster"][:5]:
            row["fixed_team"] = "A"
        before = deepcopy(state)
        with self.assertRaises(ValueError):
            core.create_match(state)
        self.assertEqual(state, before)

    def test_fixed_drafts_resting_players_rename_and_snapshots_restore(self):
        state = prepared()
        state["team_fixing_enabled"] = True
        state["roster"][0]["fixed_team"] = "B"
        state["roster"][1]["fixed_team"] = "A"
        state["roster"][7].update(active=False, fixed_team="A")
        match = core.create_match(state)
        self.assertEqual(match["fixed_teams"], {"P0": "B", "P1": "A"})
        self.assertEqual(core.import_state(core.export_state(state)), state)
        core.cancel_match(state, match["id"])
        core.edit_profile(state, "P0", dict(state["profiles"]["P0"], name="Renamed"))
        self.assertEqual(state["roster"][0]["fixed_team"], "B")
        core.undo_profile_management(state)
        self.assertEqual(state["roster"][0]["name"], "P0")
        core.reset_team_fixing(state)
        self.assertFalse(state["team_fixing_enabled"])
        self.assertFalse(any(row.get("fixed_team") for row in state["roster"]))
        self.assertEqual(core.import_state(core.export_state(state)), state)

    def test_old_backup_defaults_and_invalid_constraints(self):
        legacy = prepared()
        legacy.pop("team_fixing_enabled")
        legacy["settings"].pop("match_tolerance")
        restored = core.import_state(core.export_state(legacy))
        self.assertFalse(restored["team_fixing_enabled"])
        self.assertEqual(restored["settings"]["match_tolerance"], 25)
        for value in (-1, True, 1.5, 4 * core.MAX_RATE + 1):
            bad = deepcopy(restored)
            bad["settings"]["match_tolerance"] = value
            with self.assertRaises(ValueError):
                core.import_state(core.export_state(bad))
        bad = deepcopy(restored)
        bad["roster"][0]["fixed_team"] = "C"
        with self.assertRaises(ValueError):
            core.import_state(core.export_state(bad))


class AssignmentAppTests(unittest.TestCase):
    def start(self, state):
        at = AppTest.from_file(str(APP), default_timeout=20)
        at.session_state.store_token = "assignment-test"
        at.session_state.hydrated = True
        at.session_state.model = state
        at.run()
        self.assertFalse(at.exception)
        return at

    def press(self, at, label):
        next(b for b in at.button if b.label == label).click().run()
        self.assertFalse(at.exception)

    def test_existing_name_fills_latest_once_and_keeps_manual_rate_changes(self):
        state = core.new_state()
        state["profiles"]["既存"] = core.profile("既存", 2750)
        state["profiles"]["別人"] = core.profile("別人", 2300)
        at = self.start(state)
        at.text_input(key="name_0").set_value("既存").run()
        self.assertFalse(at.exception)
        self.assertEqual(at.text_input(key="rate_0").value, "2750")
        at.text_input(key="rate_0").set_value("２６００").run()
        at.button(key="part_toggle_0").click().run()
        self.assertEqual(at.text_input(key="rate_0").value, "２６００")
        at.button(key="toggle_team_fixing").click().run()
        at.selectbox(key="fixed_0").set_value("B").run()
        at.text_input(key="name_0").set_value("別人").run()
        self.assertFalse(at.exception)
        self.assertEqual(at.text_input(key="rate_0").value, "2300")
        self.assertEqual(at.selectbox(key="fixed_0").value, "")
        self.assertEqual(at.session_state.model["profiles"]["既存"]["rate"], 2750)

    def test_fixed_choices_can_be_reused_disabled_and_replaced_between_matches(self):
        at = self.start(prepared())
        self.assertEqual(at.number_input(key="match_tolerance").value, 25)
        at.number_input(key="match_tolerance").set_value(0).run()
        at.button(key="toggle_team_fixing").click().run()
        at.selectbox(key="fixed_0").set_value("B").run()
        at.selectbox(key="fixed_1").set_value("A").run()
        at.button(key="toggle_team_fixing").click().run()
        self.assertEqual(at.session_state.model["roster"][0]["fixed_team"], "B")
        self.press(at, "✅ チームを分ける")
        first = core.pending_match(at.session_state.model)
        self.assertNotIn("fixed_teams", first)
        self.assertEqual(first["settings"]["match_tolerance"], 0)
        self.assertTrue(at.button(key="toggle_team_fixing").disabled)
        at.radio(key=f"winner_{first['id']}").set_value("A").run()
        self.press(at, "🏆 この結果を登録する")
        at.button(key="toggle_team_fixing").click().run()
        self.assertEqual(at.selectbox(key="fixed_0").value, "B")
        at.selectbox(key="fixed_0").set_value("A").run()
        self.press(at, "✅ チームを分ける")
        second = core.pending_match(at.session_state.model)
        self.assertEqual(second["fixed_teams"], {"P0": "A", "P1": "A"})
        self.assertTrue({"P0", "P1"} <= {p["name"] for p in second["team_a"]})
        at.checkbox(key=f"cancel_{second['id']}").check().run()
        self.press(at, "試合を中止")
        self.press(at, "固定をすべて解除")
        self.assertEqual(at.button(key="toggle_team_fixing").label, "チーム固定 OFF")
        self.assertEqual(at.selectbox(key="fixed_0").value, "")
        self.assertFalse(at.session_state.model["roster"][0].get("fixed_team"))

    def test_on_off_buttons_keep_values_after_reruns_and_restore(self):
        at = self.start(prepared())
        for expected in (False, True, False, True):
            at.button(key="part_toggle_0").click().run()
            at.run()  # Browser saving can trigger another render without a new tap.
            self.assertFalse(at.exception)
            self.assertEqual(at.session_state.model["roster"][0]["active"], expected)
            self.assertEqual(at.button(key="part_toggle_0").label, "参加 ON" if expected else "参加 OFF")
        for expected in (True, False, True):
            at.button(key="toggle_team_fixing").click().run()
            at.run()
            self.assertFalse(at.exception)
            self.assertEqual(at.session_state.model["team_fixing_enabled"], expected)
            self.assertEqual(at.button(key="toggle_team_fixing").label,
                             "チーム固定 ON" if expected else "チーム固定 OFF")
        state = core.import_state(core.export_state(at.session_state.model))
        restored = self.start(state)
        self.assertEqual(restored.button(key="part_toggle_0").label, "参加 ON")
        self.assertEqual(restored.button(key="toggle_team_fixing").label, "チーム固定 ON")
        self.assertFalse(restored.selectbox(key="fixed_0").disabled)


if __name__ == "__main__":
    unittest.main()
