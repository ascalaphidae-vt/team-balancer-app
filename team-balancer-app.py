# -*- coding: utf-8 -*-
"""スプラ3オートバランス！ ブラウザ保存対応版。"""
from pathlib import Path
import uuid

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import balancer_core as core
from theme import apply_theme

APP_DIR = Path(__file__).resolve().parent
st.set_page_config(page_title="スプラ3オートバランス！", page_icon="🦑", layout="wide")
apply_theme()
browser_store = components.declare_component("team_balancer_browser_store", path=str(APP_DIR / "browser_store"))


def action(fn, *args):
    try:
        fn(st.session_state.model, *args)
        st.session_state.sync_inputs = True
        if fn is core.create_match:
            st.session_state.private_to_view = core.current_private(st.session_state.model)["id"]
        message = "プラベを終了しました。今回のメンバー表と戦績を保存し、休憩回数を0に戻しました。" if fn is core.end_private else "保存しました。"
        st.session_state.notice = ("success", message)
    except ValueError as error:
        st.session_state.notice = ("error", str(error))


def capture_roster():
    """Text changes are persisted on blur/Enter, including unfinished rate text."""
    if core.pending_match(st.session_state.model):
        return
    for i, row in enumerate(st.session_state.model["roster"]):
        row.update(name=st.session_state.get(f"name_{i}", row["name"]),
                   rate=st.session_state.get(f"rate_{i}", row["rate"]),
                   active=st.session_state.get(f"part_{i}", row["active"]))
    core.touch(st.session_state.model)


def capture_bulk():
    st.session_state.model["bulk_text"] = st.session_state.bulk_text
    core.touch(st.session_state.model)


def apply_current_bulk():
    # Read at callback time; args constructed before the textarea's blur can be stale.
    text = st.session_state.get("bulk_text", "")
    st.session_state.model["bulk_text"] = text
    action(core.apply_bulk, text)


def capture_settings():
    if core.pending_match(st.session_state.model):
        return
    st.session_state.model["settings"] = {
        "decrease": st.session_state.decrease,
        "percent": float(st.session_state.percent),
        "streak_bonus": st.session_state.streak_bonus,
    }
    core.touch(st.session_state.model)


def capture_winner(match_id):
    match = core.pending_match(st.session_state.model)
    if match and match["id"] == match_id:
        match["selected_winner"] = st.session_state[f"winner_{match_id}"]
        core.touch(st.session_state.model)


def save_profile_edit(name, keys):
    values = {field: st.session_state[key] for field, key in keys.items()}
    action(core.edit_profile, name, values)


def merge_profile_selection(source, target, initial_key, rate_key):
    action(core.merge_profiles, source, target,
           st.session_state[initial_key], st.session_state[rate_key])


def sync_inputs():
    if not st.session_state.get("sync_inputs", True):
        return
    model = st.session_state.model
    # Drop stale selections as soon as a profile is deleted, renamed, or merged.
    for key in ("profile_to_load", "manage_player", "merge_source", "merge_target"):
        if st.session_state.get(key) not in model["profiles"]:
            st.session_state.pop(key, None)
    if st.session_state.get("private_to_view") not in {p["id"] for p in model.get("private_sessions", [])}:
        st.session_state.pop("private_to_view", None)
    for i, row in enumerate(model["roster"]):
        for prefix, field in (("name", "name"), ("rate", "rate"), ("part", "active")):
            st.session_state[f"{prefix}_{i}"] = row[field]
    st.session_state.bulk_text = model["bulk_text"]
    for key, value in model["settings"].items():
        st.session_state[key] = value
    match = core.pending_match(model)
    if match:
        st.session_state[f"winner_{match['id']}"] = match.get("selected_winner")
    st.session_state.sync_inputs = False


if "store_token" not in st.session_state:
    st.session_state.store_token = uuid.uuid4().hex
    st.session_state.hydrated = False

payload = core.export_state(st.session_state.model) if st.session_state.hydrated else None
reply = browser_store(token=st.session_state.store_token, payload=payload, key="browser_store", default=None)
if not st.session_state.hydrated:
    if not reply or reply.get("token") != st.session_state.store_token:
        st.info("このブラウザの保存データを確認しています。しばらく表示が変わらない場合は再読み込みしてください。")
        st.stop()
    raw = reply.get("raw")
    try:
        if reply.get("error"):
            raise ValueError("ブラウザの保存領域が利用できません。保存を許可して再読み込みするか、一時利用を選んでください。")
        restored = core.import_state(raw) if raw is not None else core.new_state()
    except ValueError as error:
        st.error(str(error))
        if raw:
            st.download_button("読み込めなかった保存データを退避", raw, "team-balancer-recovery.txt")
        agree = st.checkbox("保存されていたデータを退避済み、または新規で開始してよい")
        if not st.button("一時利用を開始" if reply.get("error") else "新しいデータで開始", disabled=not agree):
            st.stop()
        restored = core.new_state()
    st.session_state.model = restored
    st.session_state.hydrated = True
    st.session_state.sync_inputs = True
    st.rerun()

sync_inputs()
model = st.session_state.model
match = core.pending_match(model)
locked = match is not None
notice = st.session_state.pop("notice", None)
notice_slot = st.empty()  # Keep tabs at a stable position when a notice appears/disappears.
if notice:
    getattr(notice_slot, notice[0])(notice[1])

st.title("🎮 スプラ3オートバランス！")
st.markdown("by [あすとらふぃーだ](https://x.com/Ascalaphidae) · 非公式ファンメイドツール")
st.caption("参加者を選ぶ → チーム分け → 結果を登録。入力・設定・記録は、このブラウザに自動保存します。")
st.caption("記録の手動編集・統合・削除は「📊 プレイヤーと試合記録」から行えます。")
metrics = st.columns(3)
metrics[0].metric("登録プレイヤー", len(model["profiles"]))
metrics[1].metric("結果登録済み", sum(m["status"] == "recorded" for m in model["history"]))
metrics[2].metric("結果未入力", int(locked))

private = core.current_private(model)
with st.container(border=True):
    private_status, private_end = st.columns([4, 1])
    with private_status:
        if private:
            count = sum(m["status"] == "recorded" and m.get("private_id") == private["id"] for m in model["history"])
            st.write(f"🎮 第{private['number']}回プラベ：進行中 · 結果登録 {count}試合")
            st.caption(f"開始：{private['started_at'].replace('T', ' ')[:19]} · メンバー表は「🎮 今回のプラベ」に保存します。")
        else:
            st.write("🎮 プラベ開始前：最初のチーム分けで、新しいプラベが始まります。")
            st.caption("終了した回のメンバー表・戦績は「🎮 今回のプラベ」で確認できます。休憩回数はプラベごとに数えます。")
    with private_end:
        st.button("🏁 プラベ終了", key="end_private", use_container_width=True,
                  disabled=private is None or locked, on_click=action, args=(core.end_private,))
    if locked:
        st.caption("プラベを終了する前に、未入力の試合結果を登録するか、その試合を中止してください。")


def changes_table(changes):
    return pd.DataFrame([{
        "名前": c["name"], "結果": "勝ち" if c["won"] else "負け",
        "試合前": c["before"], "変動": f"{c['delta']:+d}", "試合後": c["after"],
        "連勝・連敗": f"{abs(c['streak'])}連{'勝' if c['streak'] > 0 else '敗'}",
    } for c in changes])


if match:
    st.warning(f"第{match['number']}試合は結果未入力です。結果を登録すると次のチーム分けに進めます。")
    columns = st.columns(2)
    for col, label, field in zip(columns, ("🟩 チームA", "🟥 チームB"), ("team_a", "team_b")):
        with col:
            st.subheader(label)
            st.dataframe(pd.DataFrame([{"名前": p["name"], "レート": p["rate"]} for p in match[field]]),
                         use_container_width=True, hide_index=True)
            st.write(f"合計レート：{sum(p['rate'] for p in match[field]):,}")
    st.caption(f"合計レート差：{match['diff']:,} · 休憩：" + ("、".join(match["resting"]) or "なし"))
    if (len(match["team_a"]) + len(match["team_b"])) % 2:
        st.info("参加人数が奇数なので、チームの人数が異なります。人数差による有利・不利はレート差だけでは調整できません。")
    settings = match["settings"]
    st.caption(f"この試合の設定：変動率 {settings['percent']:g}% / 敗北時の減少 {'ON' if settings['decrease'] else 'OFF'} / 連勝・連敗補正 {'ON' if settings['streak_bonus'] else 'OFF'}")
    winner = st.radio("勝利チームを選んでください", ["A", "B"], index=None,
                      key=f"winner_{match['id']}", horizontal=True,
                      on_change=capture_winner, args=(match["id"],))
    if winner:
        st.dataframe(changes_table(core.preview_result(model, match, winner)),
                     hide_index=True, use_container_width=True)
    st.button("🏆 この結果を登録する", type="primary", disabled=winner is None,
              on_click=action, args=(core.record_result, match["id"], winner), use_container_width=True)
    with st.expander("この試合を中止する・チーム分けをやり直す"):
        st.caption("中止した試合は勝敗・レート・休憩回数に加算しません。中止の履歴は残ります。")
        confirmed = st.checkbox("この試合を記録せずに中止する", key=f"cancel_{match['id']}")
        st.button("試合を中止", disabled=not confirmed, on_click=action, args=(core.cancel_match, match["id"]))
else:
    last = next((m for m in reversed(model["history"]) if m["status"] == "recorded"), None)
    if last:
        st.success(f"第{last['number']}試合を記録済み · 勝利チーム {last['winner']} · {last['recorded_at'][11:19]}")
        with st.expander("直前の変動を確認・入力ミスを訂正"):
            st.dataframe(changes_table(last["changes"]), hide_index=True, use_container_width=True)
            st.caption("直前の結果と休憩回数を戻し、同じチームで結果を再入力できます。新しい試合のチーム分け前に操作してください。")
            blocked = core.result_reopen_reason(model, last)
            if blocked:
                st.info(blocked)
            undo = st.checkbox("直前の結果を取り消して再入力する", disabled=bool(blocked))
            st.button("直前の結果を再入力", disabled=bool(blocked) or not undo, on_click=action, args=(core.reopen_last_result,))

participants_tab, private_tab, records_tab, backup_tab, settings_tab = st.tabs(["🦑 参加者", "🎮 今回のプラベ", "📊 プレイヤーと試合記録", "💾 バックアップ", "⚙️ レート設定"])

with participants_tab:
    with st.expander("🧩 一括入力"):
        st.caption("名前：レート を改行またはカンマで区切れます。全角数字もOK。最大10人（対戦は8人まで）。レート内の桁区切りカンマは省いてください。")
        st.text_area("名前とレート", key="bulk_text", height=100, disabled=locked,
                     on_change=capture_bulk, placeholder="あすふぃだ：２６３０\nイシガケ：２０００")
        st.button("一括入力を反映", disabled=locked, on_click=apply_current_bulk)

    if model["profiles"]:
        with st.expander("📚 過去のプレイヤーを空き枠へ呼び出す"):
            name = st.selectbox("プレイヤー", sorted(model["profiles"]), key="profile_to_load", disabled=locked)
            st.caption("プレイヤー記録に現在登録されている人だけを表示します。削除・統合した旧名は表示しません。")
            source = st.radio("呼び出すレート", ["最新レート", "初期レート"], horizontal=True, disabled=locked)
            p = model["profiles"][name]
            st.caption(f"初期 {p['initial_rate']:,} / 最新 {p['rate']:,}")
            st.button("空の枠へ追加", disabled=locked, on_click=action,
                      args=(core.load_profile, name, source == "初期レート"))

    st.subheader("1. 名前を入力")
    st.caption("先に名前をまとめて入力できます。名前がある枠で参加OFFにすると、その試合は休憩として数えます。")
    for start in (0, 5):
        cols = st.columns(5)
        for offset, col in enumerate(cols):
            i = start + offset
            with col:
                st.text_input(f"名前{i + 1}", key=f"name_{i}", max_chars=80,
                              disabled=locked, on_change=capture_roster, placeholder=f"枠{i + 1}")

    st.subheader("2. レートと参加を選択")
    st.caption("レートも全角のまま入力できます（例：２６３０）。入力を確定すると自動保存されます。初期レートは「入力を登録」または初回チーム分け時の値です。")
    for start in (0, 5):
        cols = st.columns(5)
        for offset, col in enumerate(cols):
            i = start + offset
            with col:
                label = model["roster"][i]["name"].strip() or f"枠{i + 1}"
                st.text(label)
                st.text_input(f"レート{i + 1}", key=f"rate_{i}", max_chars=20,
                              disabled=locked, on_change=capture_roster)
                st.checkbox(f"参加{i + 1}", key=f"part_{i}", disabled=locked, on_change=capture_roster)
    selected_count = sum(bool(r["name"].strip()) and r["active"] for r in model["roster"])
    st.write(f"参加 {selected_count}人 / 最大8人")
    left, right = st.columns(2)
    left.button("入力を登録（初期・最新レートを保存）", on_click=action,
                args=(core.commit_roster,), disabled=locked, use_container_width=True)
    right.button("✅ チームを分ける", type="primary", on_click=action,
                 args=(core.create_match,), disabled=locked, use_container_width=True)
    with st.expander("参加者の入力枠を空にする"):
        st.caption("プレイヤーの初期・最新レート、勝敗、試合履歴は残ります。")
        clear = st.checkbox("10枠の名前・レート・参加設定を空にする", disabled=locked)
        st.button("入力枠を空にする", disabled=locked or not clear,
                  on_click=action, args=(core.reset_roster,))

with private_tab:
    st.subheader("今回・終了したプラベのメンバー一覧")
    st.caption("歴代の累計一覧とは別の、プラベごとの表です。途中参加や途中で枠から外れたメンバーも、その回で登録・チーム分けしていれば残ります。終了後の表はその時点の記録として保存します。")
    sessions = model.get("private_sessions", [])
    if sessions:
        by_id = {p["id"]: p for p in sessions}
        selected_id = st.selectbox("表示するプラベ", list(reversed(by_id)), key="private_to_view",
                                   format_func=lambda pid: f"第{by_id[pid]['number']}回 · {'進行中' if by_id[pid]['ended_at'] is None else '終了'} · {by_id[pid]['started_at'][:19].replace('T', ' ')}")
        selected = by_id[selected_id]
        finished = selected["ended_at"] is not None
        if finished:
            st.success(f"第{selected['number']}回プラベの終了時メンバー表")
            st.caption(f"終了：{selected['ended_at'].replace('T', ' ')[:19]} · 表の休憩はこの回の保存値です。現在の休憩カウンターは終了時に0へ戻しています。")
        else:
            st.info(f"第{selected['number']}回プラベは進行中です。結果登録ごとに更新します。")
        session_rows = [{"名前": p["name"], "開始時レート": p["initial_rate"],
                         "終了時レート" if finished else "現在レート": p["rate"],
                         "今回の増減": p["rate"] - p["initial_rate"], "試合": p["matches"],
                         "勝ち": p["wins"], "負け": p["losses"],
                         "勝率": f"{100 * p['wins'] / p['matches']:.1f}%" if p["matches"] else "—",
                         "休憩": p["rests"]} for p in selected["members"].values()]
        if session_rows:
            session_frame = pd.DataFrame(session_rows)
            st.dataframe(session_frame, key="private_members_table", hide_index=True, use_container_width=True)
            session_csv = session_frame.copy()
            session_csv["名前"] = session_csv["名前"].map(lambda x: "'" + x if x.startswith(("=", "+", "-", "@")) else x)
            st.download_button("このプラベのメンバー表をCSVで保存", session_csv.to_csv(index=False).encode("utf-8-sig"),
                               f"team-balancer-private-{selected['number']}.csv", "text/csv")
    else:
        st.info("最初のチーム分けで、今回のプラベの記録を開始します。")
        st.caption("この機能の導入前の試合は、歴代の戦績・試合履歴に引き続き残ります。開始・終了の区切りがないため、今回の表へはさかのぼって分類しません。")

with records_tab:
    st.subheader("歴代のプレイヤー記録（累計戦績）")
    st.caption("勝敗・試合数・レートはプラベ終了後も保持します。休憩は今回分で、プラベ終了時に0へ戻ります。連勝・連敗は休憩やプラベ終了では中断しません。")
    if model["profiles"]:
        rows = []
        for p in model["profiles"].values():
            rows.append({"名前": p["name"], "初期レート": p["initial_rate"], "最新レート": p["rate"],
                         "初期からの増減": p["rate"] - p["initial_rate"], "試合": p["matches"],
                         "勝ち": p["wins"], "負け": p["losses"],
                         "勝率": f"{100 * p['wins'] / p['matches']:.1f}%" if p["matches"] else "—",
                         "今回の休憩": p["rests"], "連勝・連敗": f"{abs(p['streak'])}連{'勝' if p['streak'] > 0 else '敗'}" if p["streak"] else "—"})
        frame = pd.DataFrame(rows)
        st.dataframe(frame, hide_index=True, use_container_width=True)
        safe_csv = frame.copy()
        safe_csv["名前"] = safe_csv["名前"].map(lambda x: "'" + x if x.startswith(("=", "+", "-", "@")) else x)
        st.download_button("プレイヤー記録をCSVで保存", safe_csv.to_csv(index=False).encode("utf-8-sig"),
                           "team-balancer-records.csv", "text/csv")
    else:
        st.info("入力を登録するとプレイヤーがここに保存されます。")

    st.subheader("プレイヤー記録の編集・統合・削除")
    st.caption("過去の試合履歴は当時の名前・レートのまま残します。整理・編集後は、それ以前の試合結果の取り消しを停止します。整理・編集自体は、次にデータを変更するまで直前の1回を元に戻せます。")
    if locked:
        st.info("未入力の試合結果を登録するか中止すると、記録を整理・編集できます。")
    management_undo = model.get("profile_management_undo")
    if management_undo:
        st.button(f"↩ 直前の整理・編集を元に戻す（{management_undo['label']}）",
                  key="undo_profile_management", disabled=locked,
                  on_click=action, args=(core.undo_profile_management,))
    if model["profiles"]:
        registered_names = sorted(model["profiles"])
        person = st.selectbox("編集・削除するプレイヤー", registered_names,
                              key="manage_player", disabled=locked)
        p = model["profiles"][person]
        with st.expander("✏️ 手入力で編集する"):
            st.caption("勝敗数は歴代の累計値です。試合数・勝率は勝敗数から自動計算します。休憩は今回分（終了時に0）。今回の勝敗表は実際の試合結果から集計します。連勝は正、連敗は負（3連敗は -3）、連続なしは0です。")
            edit_prefix = f"profile_edit_{person}_{model['revision']}"
            fields = ("name", "initial_rate", "rate", "wins", "losses", "rests", "streak")
            edit_keys = {field: f"{edit_prefix}_{field}" for field in fields}
            with st.form(f"{edit_prefix}_form"):
                st.text_input("記録のプレイヤー名", value=person, key=edit_keys["name"], max_chars=80, disabled=locked)
                col1, col2 = st.columns(2)
                col1.text_input("記録の初期レート", value=str(p["initial_rate"]), key=edit_keys["initial_rate"], disabled=locked)
                col2.text_input("記録の最新レート", value=str(p["rate"]), key=edit_keys["rate"], disabled=locked)
                cols = st.columns(4)
                for col, field, label in zip(cols, ("wins", "losses", "rests", "streak"),
                                             ("記録の勝利数", "記録の敗北数", "記録の休憩回数", "記録の連勝・連敗")):
                    col.number_input(label, min_value=-1_000_000_000 if field == "streak" else 0,
                                     max_value=1_000_000_000, value=p[field], step=1,
                                     key=edit_keys[field], disabled=locked)
                st.form_submit_button("手動編集を保存", type="primary", disabled=locked,
                                      on_click=save_profile_edit, args=(person, edit_keys))

        with st.expander("🔗 同じ人物の記録を統合する"):
            if len(registered_names) < 2:
                st.info("統合には2人以上の登録が必要です。")
            else:
                source = st.selectbox("統合して消す名前", registered_names, key="merge_source", disabled=locked)
                destinations = [n for n in registered_names if n != source]
                target = st.selectbox("残す名前（統合先）", destinations, key="merge_target", disabled=locked)
                a, b = model["profiles"][source], model["profiles"][target]
                st.write(f"統合後：{a['wins'] + b['wins']}勝 / {a['losses'] + b['losses']}敗 / 休憩 {a['rests'] + b['rests']}回")
                st.caption("勝敗・休憩は合算し、連勝・連敗は統合先の値を残します。同じ試合に両方の名前を入れていた場合も合算するため、必要に応じて統合後に手動で調整してください。参加者枠に両方いる場合は1枠にまとめます。")
                merge_prefix = f"merge_{source}_{target}_{model['revision']}"
                initial_key, rate_key = merge_prefix + "_initial", merge_prefix + "_rate"
                for label, key, field in (("統合後の初期レート", initial_key, "initial_rate"),
                                          ("統合後の最新レート", rate_key, "rate")):
                    st.radio(label, ["target", "source"], horizontal=True, key=key, disabled=locked,
                             format_func=lambda side, f=field: f"{target if side == 'target' else source}：{(b if side == 'target' else a)[f]}")
                agreed = st.checkbox("この2つの名前は同じ人物です", key=merge_prefix + "_confirm", disabled=locked)
                st.button("この2人の記録を統合", disabled=locked or not agreed,
                          on_click=merge_profile_selection, args=(source, target, initial_key, rate_key))

        with st.expander("🗑️ 不要なプレイヤーを削除する"):
            st.caption("プレイヤー記録・呼び出し一覧・現在の参加者枠から外します。過去の試合履歴は残ります。")
            agreed = st.checkbox(f"「{person}」をプレイヤー記録から削除する",
                                 key=f"delete_{person}_{model['revision']}", disabled=locked)
            st.button("選んだプレイヤーを削除", disabled=locked or not agreed,
                      on_click=action, args=(core.delete_profile, person))

    st.subheader("試合履歴")
    if model["history"]:
        history_rows = [{"試合": m["number"], "日時": m["created_at"].replace("T", " ")[:19],
                         "プラベ": next((f"第{p['number']}回" for p in model.get("private_sessions", []) if p["id"] == m.get("private_id")), "導入前"),
                         "状態": {"pending": "結果未入力", "recorded": "記録済み", "void": "中止"}[m["status"]],
                         "チームA": "、".join(p["name"] for p in m["team_a"]),
                         "チームB": "、".join(p["name"] for p in m["team_b"]),
                         "勝利": m["winner"] or "—", "休憩": "、".join(m["resting"])}
                        for m in reversed(model["history"])]
        st.dataframe(pd.DataFrame(history_rows), hide_index=True, use_container_width=True)
        chosen = st.selectbox("レート変動を確認する試合", list(reversed(model["history"])),
                              format_func=lambda m: f"第{m['number']}試合 · {m['created_at'][:19]}")
        if chosen["status"] == "recorded":
            st.dataframe(changes_table(chosen["changes"]), hide_index=True, use_container_width=True)
    else:
        st.info("チーム分けをすると試合履歴が作られます。")

with backup_tab:
    st.subheader("保存とバックアップ")
    st.write("同じ端末・同じブラウザ・同じアプリURLで、次回も自動復元します。ブラウザのデータ削除やシークレットモードでは保存が失われるため、大事な記録はバックアップしてください。")
    st.caption("入力中の文字はEnterまたは入力欄からフォーカスを移した時点で保存対象になります。画面上部の「保存済み」を確認してから閉じてください。端末間の自動共有はありません。")
    st.download_button("📥 全データのバックアップ", core.export_state(model).encode("utf-8"),
                       "team-balancer-backup.json", "application/json", use_container_width=True)
    uploaded = st.file_uploader("JSONバックアップから復元", type=["json"], disabled=locked)
    replace = st.checkbox("バックアップの内容で現在の入力・全記録を置き換える", disabled=locked)
    if st.button("バックアップを復元", disabled=locked or uploaded is None or not replace):
        try:
            restored = core.import_state(uploaded.getvalue().decode("utf-8-sig"))
            core.touch(restored)
            st.session_state.model = restored
            st.session_state.sync_inputs = True
            st.session_state.notice = ("success", "バックアップを復元しました。")
            st.rerun()
        except (ValueError, UnicodeDecodeError) as error:
            st.error(str(error))
    with st.expander("旧版の登録リスト（テキスト）を取り込む"):
        st.caption("旧版の 名前：レート のテキストに対応します。既存プレイヤーの初期レートは保持し、最新レートを更新します。")
        legacy = st.text_area("旧版の登録リスト", disabled=locked)
        if st.button("登録リストを取り込む", disabled=locked):
            try:
                imported = core.parse_bulk(legacy, limit=None)
                for row in imported:
                    name, rate = row["name"], int(row["rate"])
                    if name not in model["profiles"]:
                        model["profiles"][name] = core.profile(name, rate)
                        model.get("profile_links", {}).pop(name, None)
                    else:
                        model["profiles"][name]["rate"] = rate
                core.sync_rates(model, {r["name"] for r in imported})
                core.touch(model)
                st.session_state.sync_inputs = True
                st.session_state.notice = ("success", f"{len(imported)}人の登録リストを取り込みました。")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

with settings_tab:
    st.subheader("レート変動の設定")
    st.checkbox("負けたときにレートを減らす（標準ON）", key="decrease", on_change=capture_settings, disabled=locked)
    st.number_input("基本変動率（%）", min_value=0.0, max_value=20.0, step=0.5,
                    key="percent", on_change=capture_settings, disabled=locked)
    st.checkbox("連勝・連敗で変動を大きくする", key="streak_bonus", on_change=capture_settings, disabled=locked)
    st.markdown("連勝・連敗の **1回目は1倍、2回目は1.25倍、3回目は1.5倍、4回目は1.75倍、5回目以降は2倍**。勝敗が変わると1回目から数え直します。休憩は連勝・連敗を中断しません。")
    st.caption("例：レート2000・変動率3%なら、初回は±60、2連続なら±75。実際の計算は各試合直前のレートが基準です。小数は四捨五入、最低変動1（変動率0%は0）、レート範囲0〜999999。減少OFFでは負けてもレートは変わりません。")
    if locked:
        st.info("結果未入力の試合があります。設定は結果登録後に変更できます。")

st.divider()
if (APP_DIR / "assets" / ("character_assigned.png" if locked else "character_start.png")).is_file():
    _, col = st.columns([4, 1])
    with col:
        st.image(str(APP_DIR / "assets" / ("character_assigned.png" if locked else "character_start.png")), width=150)
st.caption("非公式ファンメイドツール · by あすとらふぃーだ")
