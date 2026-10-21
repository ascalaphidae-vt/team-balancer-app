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
        st.session_state.notice = ("success", "保存しました。")
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


def sync_inputs():
    if not st.session_state.get("sync_inputs", True):
        return
    model = st.session_state.model
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
if notice:
    getattr(st, notice[0])(notice[1])

st.title("🎮 スプラ3オートバランス！")
st.markdown("by [あすとらふぃーだ](https://x.com/Ascalaphidae) · 非公式ファンメイドツール")
st.caption("参加者を選ぶ → チーム分け → 結果を登録。入力・設定・記録は、このブラウザに自動保存します。")
metrics = st.columns(3)
metrics[0].metric("登録プレイヤー", len(model["profiles"]))
metrics[1].metric("結果登録済み", sum(m["status"] == "recorded" for m in model["history"]))
metrics[2].metric("結果未入力", int(locked))


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
            undo = st.checkbox("直前の結果を取り消して再入力する")
            st.button("直前の結果を再入力", disabled=not undo, on_click=action, args=(core.reopen_last_result,))

participants_tab, records_tab, backup_tab, settings_tab = st.tabs(["🦑 参加者", "📊 プレイヤーと試合記録", "💾 バックアップ", "⚙️ レート設定"])

with participants_tab:
    with st.expander("🧩 一括入力"):
        st.caption("名前：レート を改行またはカンマで区切れます。全角数字もOK。最大10人（対戦は8人まで）。レート内の桁区切りカンマは省いてください。")
        st.text_area("名前とレート", key="bulk_text", height=100, disabled=locked,
                     on_change=capture_bulk, placeholder="あすふぃだ：２６３０\nイシガケ：２０００")
        st.button("一括入力を反映", disabled=locked, on_click=apply_current_bulk)

    if model["profiles"]:
        with st.expander("📚 過去のプレイヤーを空き枠へ呼び出す"):
            name = st.selectbox("プレイヤー", sorted(model["profiles"]), key="profile_to_load", disabled=locked)
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

with records_tab:
    st.subheader("プレイヤー記録")
    st.caption("同じ名前を同じプレイヤーとして集計します。初期レートは最初の登録時の値で、その後の更新でも保持します。休憩は結果登録時に数え、連勝・連敗は中断しません。")
    if model["profiles"]:
        rows = []
        for p in model["profiles"].values():
            rows.append({"名前": p["name"], "初期レート": p["initial_rate"], "最新レート": p["rate"],
                         "初期からの増減": p["rate"] - p["initial_rate"], "試合": p["matches"],
                         "勝ち": p["wins"], "負け": p["losses"],
                         "勝率": f"{100 * p['wins'] / p['matches']:.1f}%" if p["matches"] else "—",
                         "休憩": p["rests"], "連勝・連敗": f"{abs(p['streak'])}連{'勝' if p['streak'] > 0 else '敗'}" if p["streak"] else "—"})
        frame = pd.DataFrame(rows)
        st.dataframe(frame, hide_index=True, use_container_width=True)
        safe_csv = frame.copy()
        safe_csv["名前"] = safe_csv["名前"].map(lambda x: "'" + x if x.startswith(("=", "+", "-", "@")) else x)
        st.download_button("プレイヤー記録をCSVで保存", safe_csv.to_csv(index=False).encode("utf-8-sig"),
                           "team-balancer-records.csv", "text/csv")
    else:
        st.info("入力を登録するとプレイヤーがここに保存されます。")
    st.subheader("試合履歴")
    if model["history"]:
        history_rows = [{"試合": m["number"], "日時": m["created_at"].replace("T", " ")[:19],
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
    col, _ = st.columns([1, 4])
    with col:
        st.image(str(APP_DIR / "assets" / ("character_assigned.png" if locked else "character_start.png")), width=150)
st.caption("非公式ファンメイドツール · by あすとらふぃーだ")
