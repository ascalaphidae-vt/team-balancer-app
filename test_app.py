from pathlib import Path
from contextlib import contextmanager
from copy import deepcopy
import sys
import types
import unittest
from streamlit.testing.v1 import AppTest
import balancer_core as c

APP = Path(__file__).with_name("team-balancer-app.py")


class AppTests(unittest.TestCase):
    def start(self, state=None):
        at = AppTest.from_file(str(APP), default_timeout=20)
        at.session_state.store_token = "test"
        at.session_state.hydrated = True
        at.session_state.model = state or c.new_state()
        at.run()
        self.assertEqual(len(at.exception), 0)
        return at

    def button(self, at, label):
        return next(b for b in at.button if b.label == label)

    def legacy_module(self):
        module = types.ModuleType("balancer_core")
        module.__dict__.update({k: v for k, v in vars(c).items()
                                if k not in ("current_private", "end_private", "result_reopen_reason")})
        return module

    @contextmanager
    def stale_core_cache(self):
        original = sys.modules.get("balancer_core")
        sys.modules["balancer_core"] = self.legacy_module()
        try:
            yield
        finally:
            if original is None:
                sys.modules.pop("balancer_core", None)
            else:
                sys.modules["balancer_core"] = original

    def legacy_state(self, games=1):
        state = c.new_state()
        c.apply_bulk(state, "甲:2000,乙:2000,休憩さん:2000")
        state["roster"][2]["active"] = False
        for _ in range(games):
            match = c.create_match(state)
            c.record_result(state, match["id"], "A")
        state.pop("private_sessions")
        for match in state["history"]:
            match.pop("private_id")
            match.pop("private_members_before", None)
        return state

    def test_stale_module_does_not_break_new_ui_or_destroy_30_players_29_matches(self):
        state = self.legacy_state(games=29)
        for i in range(27):
            name = f"歴代{i}"
            state["profiles"][name] = c.profile(name, 2000)
        original = c.export_state(state)
        with self.stale_core_cache():
            at = self.start(state)
            self.assertEqual(len(at.session_state.model["profiles"]), 30)
            self.assertEqual(len(at.session_state.model["history"]), 29)
            migrated = at.session_state.model
            self.assertEqual(c.export_state({k: v for k, v in migrated.items() if k != "private_sessions"}), original)
            self.assertEqual(migrated["private_sessions"], [])
            self.button(at, "✅ チームを分ける").click().run()
            self.assertFalse(at.exception)
            match = c.pending_match(at.session_state.model)
            at.radio(key=f"winner_{match['id']}").set_value("B").run()
            self.button(at, "🏆 この結果を登録する").click().run()
            at.button(key="end_private").click().run()
            self.assertFalse(at.exception)
            self.assertEqual(len(at.session_state.model["history"]), 30)
            self.assertEqual(at.session_state.model["profiles"]["甲"]["matches"], 30)
            self.assertEqual(at.session_state.model["profiles"]["休憩さん"]["rests"], 0)

    def test_warm_upgrade_adopts_legacy_pending_without_losing_past_results(self):
        state = self.legacy_state()
        # Build an old-format pending match without inventing a result.
        pending = deepcopy(state["history"][0])
        pending.update(id="legacy-pending", number=2, status="pending", winner=None, changes=[])
        pending.pop("profiles_before")
        pending.pop("recorded_at")
        for p in pending["team_a"] + pending["team_b"]:
            p["rate"] = state["profiles"][p["name"]]["rate"]
        pending["diff"] = abs(sum(p["rate"] for p in pending["team_a"]) - sum(p["rate"] for p in pending["team_b"]))
        state["history"].append(pending)
        with self.stale_core_cache():
            at = self.start(state)
            self.assertFalse(at.exception)
            self.assertEqual(len(at.session_state.model["history"]), 2)
            self.assertEqual(c.pending_match(at.session_state.model)["id"], "legacy-pending")
            self.assertTrue(at.button(key="end_private").disabled)
            at.radio(key="winner_legacy-pending").set_value("A").run()
            self.button(at, "🏆 この結果を登録する").click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.session_state.model["profiles"]["甲"]["matches"], 2)

    def test_invalid_warm_upgrade_preserves_original_and_offers_backup(self):
        state = self.legacy_state()
        state["profiles"]["甲"]["matches"] = -1
        before = c.export_state(state)
        at = self.start(state)
        self.assertTrue(at.error)
        self.assertFalse(at.exception)
        self.assertEqual(c.export_state(at.session_state.model), before)
        self.assertEqual(len(at.get("download_button")), 1)

    def test_edit_assign_result_reopen_without_widget_exception(self):
        at = self.start()
        for i, name in enumerate(("あすふぃだ", "イシガケ", "休憩さん")):
            at.text_input(key=f"name_{i}").set_value(name).run()
            at.text_input(key=f"rate_{i}").set_value("２０００").run()
            if i < 2: at.checkbox(key=f"part_{i}").check().run()
        self.button(at, "✅ チームを分ける").click().run()
        self.assertEqual(len(at.exception), 0)
        m = c.pending_match(at.session_state.model)
        self.assertIsNotNone(m)
        self.assertTrue(at.text_input(key="name_0").disabled)
        self.assertIsNone(at.radio(key=f"winner_{m['id']}").value)
        self.assertTrue(self.button(at, "🏆 この結果を登録する").disabled)
        at.radio(key=f"winner_{m['id']}").set_value("B").run()
        self.button(at, "🏆 この結果を登録する").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertIsNone(c.pending_match(at.session_state.model))
        self.assertEqual(at.session_state.model["profiles"]["休憩さん"]["rests"], 1)
        self.assertNotEqual(at.text_input(key="rate_0").value, "2000")
        next(x for x in at.checkbox if x.label == "直前の結果を取り消して再入力する").check().run()
        self.button(at, "直前の結果を再入力").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertIsNotNone(c.pending_match(at.session_state.model))
        self.assertEqual(at.session_state.model["profiles"]["休憩さん"]["rests"], 0)
        self.assertIsNone(at.radio(key=f"winner_{m['id']}").value)

    def test_invalid_input_is_preserved_and_does_not_create_match(self):
        at = self.start()
        at.text_area(key="bulk_text").set_value("A:２０００,B:２０００").run()
        self.button(at, "一括入力を反映").click().run()
        self.assertEqual(at.text_input(key="name_0").value, "A")
        at.text_input(key="rate_0").set_value("入力途中").run()
        self.button(at, "✅ チームを分ける").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(at.error)
        self.assertEqual(at.text_input(key="rate_0").value, "入力途中")
        self.assertIsNone(c.pending_match(at.session_state.model))

    def test_restore_populates_fullwidth_drafts_settings_and_pending(self):
        state = c.new_state()
        c.apply_bulk(state, "甲:2000,乙:2000")
        state["settings"]["decrease"] = False
        m = c.create_match(state)
        m["selected_winner"] = "A"
        at = self.start(c.import_state(c.export_state(state)))
        self.assertEqual(at.text_input(key="name_0").value, "甲")
        self.assertFalse(at.checkbox(key="decrease").value)
        self.assertEqual(at.radio(key=f"winner_{m['id']}").value, "A")
        self.assertTrue(self.button(at, "✅ チームを分ける").disabled)

    def registered(self):
        state = c.new_state()
        c.apply_bulk(state, "あお:2000,別名:2500,みどり:1800")
        return self.start(state)

    def by_label(self, elements, label):
        return next(w for w in elements if w.label == label)

    def test_manual_editor_saves_all_fields_and_refreshes_call_list(self):
        at = self.registered()
        at.selectbox(key="manage_player").set_value("あお").run()
        self.by_label(at.text_input, "記録のプレイヤー名").set_value("あお正式名")
        self.by_label(at.text_input, "記録の最新レート").set_value("２７００")
        self.by_label(at.number_input, "記録の勝利数").set_value(7)
        self.by_label(at.number_input, "記録の敗北数").set_value(2)
        self.by_label(at.number_input, "記録の休憩回数").set_value(3)
        self.by_label(at.number_input, "記録の連勝・連敗").set_value(4)
        self.button(at, "手動編集を保存").click().run()
        self.assertFalse(at.exception)
        p = at.session_state.model["profiles"]["あお正式名"]
        self.assertEqual((p["rate"], p["matches"], p["rests"], p["streak"]), (2700, 9, 3, 4))
        self.assertNotIn("あお", at.selectbox(key="profile_to_load").options)
        self.assertIn("あお正式名", at.selectbox(key="profile_to_load").options)

    def test_merge_then_delete_and_restore_last_person(self):
        at = self.registered()
        at.selectbox(key="merge_source").set_value("別名").run()
        at.selectbox(key="merge_target").set_value("あお").run()
        self.by_label(at.checkbox, "この2つの名前は同じ人物です").check().run()
        self.button(at, "この2人の記録を統合").click().run()
        self.assertFalse(at.exception)
        self.assertNotIn("別名", at.selectbox(key="profile_to_load").options)
        at.selectbox(key="manage_player").set_value("あお").run()
        self.by_label(at.checkbox, "「あお」をプレイヤー記録から削除する").check().run()
        self.button(at, "選んだプレイヤーを削除").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.selectbox(key="profile_to_load").options, ["みどり"])
        at.button(key="undo_profile_management").click().run()
        self.assertFalse(at.exception)
        self.assertIn("あお", at.selectbox(key="profile_to_load").options)
        self.assertNotIn("別名", at.selectbox(key="profile_to_load").options)

    def test_delete_last_profile_and_undo_remain_available(self):
        state = c.new_state()
        c.apply_bulk(state, "ひとり:2000")
        at = self.start(state)
        self.by_label(at.checkbox, "「ひとり」をプレイヤー記録から削除する").check().run()
        self.button(at, "選んだプレイヤーを削除").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(at.session_state.model["profiles"])
        at.button(key="undo_profile_management").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.selectbox(key="profile_to_load").options, ["ひとり"])

    def test_private_end_resets_live_counter_and_keeps_separate_members_table(self):
        s = c.new_state()
        c.apply_bulk(s, "甲:2000,乙:2000,休憩さん:2000")
        s["roster"][2]["active"] = False
        at = self.start(s)
        self.assertTrue(at.button(key="end_private").disabled)
        self.button(at, "✅ チームを分ける").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(at.button(key="end_private").disabled)
        m = c.pending_match(at.session_state.model)
        at.radio(key=f"winner_{m['id']}").set_value("A").run()
        self.button(at, "🏆 この結果を登録する").click().run()
        self.assertFalse(at.button(key="end_private").disabled)
        self.assertEqual(at.session_state.model["profiles"]["休憩さん"]["rests"], 1)
        at.button(key="end_private").click().run()
        self.assertFalse(at.exception)
        state = at.session_state.model
        self.assertIsNone(c.current_private(state))
        self.assertEqual(state["profiles"]["休憩さん"]["rests"], 0)
        self.assertEqual(state["profiles"]["甲"]["matches"], 1)
        table = next(df.value for df in at.dataframe if "終了時レート" in df.value.columns)
        self.assertEqual(table.loc[table["名前"] == "休憩さん", "休憩"].iloc[0], 1)
        self.assertTrue(self.button(at, "直前の結果を再入力").disabled)
        self.button(at, "✅ チームを分ける").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(c.current_private(at.session_state.model)["number"], 2)
        self.assertEqual(len(at.selectbox(key="private_to_view").options), 2)

    def test_private_view_restores_closed_tables_and_can_select_past_private(self):
        s = c.new_state()
        c.apply_bulk(s, "甲:2000,乙:2000")
        first = c.create_match(s)
        c.record_result(s, first["id"], "A")
        c.end_private(s)
        c.create_match(s)
        at = self.start(c.import_state(c.export_state(s)))
        self.assertFalse(at.exception)
        at.selectbox(key="private_to_view").set_value(s["private_sessions"][0]["id"]).run()
        self.assertFalse(at.exception)
        table = next(df.value for df in at.dataframe if "終了時レート" in df.value.columns)
        self.assertEqual(set(table["名前"]), {"甲", "乙"})
        self.assertEqual(table["試合"].sum(), 2)


if __name__ == "__main__":
    unittest.main()
