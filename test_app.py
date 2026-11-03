from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
