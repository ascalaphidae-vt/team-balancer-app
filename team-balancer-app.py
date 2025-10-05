# -*- coding: utf-8 -*-
# Streamlit app: スプラ3オートバランス！ by あすとらふぃーだ
# 追加機能: ① プレイヤー一括入力（「名前：レート, 名前：レート, ...」）

import re
import itertools
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


X_URL = "https://x.com/Ascalaphidae"  # 例: "https://x.com/your_handle"

st.set_page_config(page_title="スプラ3オートバランス！", layout="wide")

# =========================
# セッション変数 初期化
# =========================
if "stage" not in st.session_state:
    # start -> フォーム入力中
    # assigned -> 「チームを分ける」押下直後（編成処理トリガ）
    # assigned_done -> チーム表示中
    # updated -> レート更新後
    st.session_state.stage = "start"

# プレイヤー 10枠（(name, rate) のタプル）
if "players" not in st.session_state:
    st.session_state.players = [("", 2000) for _ in range(10)]

# 参加チェック（10枠ぶん）
if "participate" not in st.session_state:
    st.session_state.participate = [False for _ in range(10)]

# 一括入力保持
if "bulk_input" not in st.session_state:
    st.session_state.bulk_input = ""

# ===== ここを変更：タイトル + 控えめな "by" をクリックでXリンク =====
st.markdown(
    f"""
    <h1 style="margin-bottom:0.2rem;">🎮 スプラ3オートバランス！</h1>
    <div style="font-size:0.95rem; opacity:0.85; margin-bottom:1rem;">
      by <a href="{X_URL}" target="_blank" style="text-decoration:none;">あすとらふぃーだ</a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("""
ゲームのレートに応じて最適なチーム分けを行い、勝利チームのレートを更新できます ✨

---

### 🕹️ つかいかた（追記：一括入力対応）
- 下の **「🧩 一括入力」** に `名前：レート, 名前：レート, ...` の形式で入れて **反映** を押すと、
  プレイヤー1から順に **名前** と **レート** が一括反映されます。（全角/半角のコロン・カンマOK。改行や「、」「；」「;」でも区切れます）
- 一括反映された枠は **参加する** が自動でONになります。不要な枠はOFFにしてください。
- 「✅ チームを分ける」を押すと、**参加ONかつ名前が入っている人だけ**でチーム分けします。
  - **本アプリは非公式のファンメイドツールです**
""")

# =========================
# ① 一括入力 UI
# =========================
st.subheader("🧩 一括入力（プレイヤー名とレート）")
st.caption("例： あすふぃだ：2400, イシガケ：2000, ウスバキ：1800（全角/半角の：, 、 ; 改行などもOK）")
st.session_state.bulk_input = st.text_area(
    "形式：名前：レート をカンマ等で区切って入力（最大10人まで）",
    value=st.session_state.bulk_input,
    height=90,
    placeholder="あすふぃだ：2400, イシガケ：2000, ウスバキ：1800"
)

def _parse_and_apply_bulk():
    raw = st.session_state.bulk_input or ""
    # 区切りをカンマに正規化（読点・セミコロン・改行など）
    s = raw.replace("\n", ",")
    s = re.sub(r"[、；;]", ",", s)
    entries = [e.strip() for e in s.split(",") if e.strip()]
    applied = 0
    errors = []
    idx = 0

    for e in entries:
        # コロン（全角/半角）で name:rate に分割
        if "：" in e:
            parts = e.split("：", 1)
        elif ":" in e:
            parts = e.split(":", 1)
        else:
            errors.append(f"区切り（: または ：）が見つかりません: {e}")
            continue

        name = parts[0].strip()
        rate_str = parts[1].strip()

        if not name:
            errors.append(f"名前が空です: {e}")
            continue

        # 全角数字を半角へ
        rate_str = rate_str.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
        if not re.fullmatch(r"\d+", rate_str):
            errors.append(f"レートが数値ではありません: {e}")
            continue

        rate = max(0, int(rate_str))

        if idx < 10:
            st.session_state.players[idx] = (name, rate)
            st.session_state.participate[idx] = True  # 反映枠は参加ON
            idx += 1
            applied += 1
        else:
            errors.append(f"10枠を超えたためスキップ: {e}")

    if applied > 0:
        st.success(f"✅ {applied}人を一括反映しました（参加ON）。")
    if errors:
        st.warning("⚠️ 次の項目は反映できませんでした：\n- " + "\n- ".join(errors))

st.button("反映", type="primary", on_click=_parse_and_apply_bulk)

# =========================
# 個別入力フォーム
# =========================
st.subheader("🦑 プレイヤー情報の入力（個別） 🐙")
st.markdown("各プレイヤーの名前・レート・参加可否を調整してください。")

with st.form(key="player_form"):
    reset_col, _ = st.columns([1, 5])
    with reset_col:
        if st.form_submit_button("🔄 入力をリセット"):
            st.session_state.players = [("", 2000) for _ in range(10)]
            st.session_state.participate = [False for _ in range(10)]
            st.session_state.stage = "start"
            if "best_team_a" in st.session_state:
                del st.session_state["best_team_a"]
            if "best_team_b" in st.session_state:
                del st.session_state["best_team_b"]
            st.rerun()

    cols = st.columns([1]*10)
    for i in range(10):
        with cols[i]:
            st.markdown(f"**枠{i+1}**")
            name = st.text_input(f"名前{i+1}", value=st.session_state.players[i][0], key=f"name_{i}")
            rate = st.number_input(
                f"レート{i+1}",
                min_value=0,
                value=int(st.session_state.players[i][1]),
                step=50,
                key=f"rate_{i}"
            )
            part = st.checkbox(
                "参加する",
                value=st.session_state.participate[i],
                key=f"part_{i}"
            )
            # ウィジェットの値をソース・オブ・トゥルースとして players に反映
            st.session_state.players[i] = (name, int(rate))
            st.session_state.participate[i] = bool(part)

    submit = st.form_submit_button("✅ チームを分ける")
    if submit:
        st.session_state.stage = "assigned"

# =========================
# チーム分けロジック
# =========================
def assign_teams(players_list):
    """
    与えられた (name, rate) のリストを2チームに最小差で分割。
    片方の人数は floor(n/2)。もう片方は n - floor(n/2)。
    """
    n = len(players_list)
    if n < 2:
        return [], [], None

    k = n // 2  # チームAの人数
    min_diff = float("inf")
    best_a, best_b = [], []

    # 組み合わせ全探索（最大8名までなので計算量は十分軽い：C(8,4)=70）
    for combo in itertools.combinations(players_list, k):
        team_a = list(combo)
        team_b = [p for p in players_list if p not in team_a]
        sum_a = sum(p[1] for p in team_a)
        sum_b = sum(p[1] for p in team_b)
        diff = abs(sum_a - sum_b)
        if diff < min_diff:
            min_diff = diff
            best_a, best_b = team_a, team_b

    return best_a, best_b, min_diff

# =========================
# チーム編成 実行
# =========================
if st.session_state.get("stage") == "assigned" and submit:
    # 「参加ON」かつ「名前が非空」だけを抽出
    selected = [
        (n, r)
        for (n, r), use in zip(st.session_state.players, st.session_state.participate)
        if use and str(n).strip() != ""
    ]
    n_sel = len(selected)

    # ③ 9人以上はエラー（ゲーム上限8）
    if n_sel >= 9:
        st.session_state.stage = "start"
        if "best_team_a" in st.session_state:
            del st.session_state["best_team_a"]
        if "best_team_b" in st.session_state:
            del st.session_state["best_team_b"]
        st.error("❌ 参加者が9人以上です。ゲームは最大8人までです。チェックを外して再実行してください。")
    else:
        if n_sel < 2:
            st.warning("⚠️ 2人以上選んでください。（名前が空欄だと無視されます）")
        else:
            # ④ 7人以下でもOK（自動で最小差分割）
            a, b, diff = assign_teams(selected)
            st.session_state.best_team_a = a
            st.session_state.best_team_b = b
            st.session_state.stage = "assigned_done"
            st.success(f"💡 チーム分けしました！ 参加人数: {n_sel} / レート差: {diff}")

# =========================
# 状況に応じた画像（任意）
# =========================
if st.session_state.stage in ("start", "updated"):
    img_url = "https://cdn.discordapp.com/attachments/1291365679429189632/1362413372217364784/1.png?ex=68024dd4&is=6800fc54&hm=12d406f6e7bbda55e86f2fcbf700164ad03b8ce1142bd1766d449d383f2cf7a7&"
elif st.session_state.stage in ("assigned", "assigned_done"):
    img_url = "https://cdn.discordapp.com/attachments/1291365679429189632/1362413397353693184/2.png?ex=68024dda&is=6800fc5a&hm=7537e4ecb893d42b6d028bc267f8e53b701d7e3b021fc9ea4a66b92dbe323f14&"
else:
    img_url = ""

if img_url:
    components.html(f"""
    <script>
    function confirmAndRedirect() {{
        if (confirm('あすとらふぃーだのチャンネルを表示する？')) {{
            window.open('https://www.youtube.com/channel/UCjJbi4Fs5kZIRAVWvNBPOpA', '_blank');
        }}
    }}
    </script>
    <div style='position: fixed; bottom: 1rem; right: 1rem; z-index: 5;'>
        <img src='{img_url}' width='170' style='opacity: 0.85; border-radius: 10px; cursor: pointer;' onclick='confirmAndRedirect()'>
    </div>
    """, height=260)

# =========================
# チーム表示 & レート更新
# =========================
if "best_team_a" in st.session_state and "best_team_b" in st.session_state:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🟦 チームA")
        df_a = pd.DataFrame(st.session_state.best_team_a, columns=["名前", "レート"])
        st.dataframe(df_a, use_container_width=True)
        st.markdown(f"**合計パワー：{int(df_a['レート'].sum())}**")

    with col2:
        st.markdown("### 🟨 チームB")
        df_b = pd.DataFrame(st.session_state.best_team_b, columns=["名前", "レート"])
        st.dataframe(df_b, use_container_width=True)
        st.markdown(f"**合計パワー：{int(df_b['レート'].sum())}**")

    st.divider()
    st.subheader("🏆 勝利チームのレート更新")

    win_team = st.radio("どちらのチームが勝ちましたか？", ["A", "B"], horizontal=True)
    multiplier = st.number_input("更新倍率（例：1.03 = 3%加算）", value=1.03, step=0.01)

    # ★ 修正ポイント：players と rate_i ウィジェットの state を両方更新してから rerun
    if st.button("📈 レートを更新する"):
        st.session_state.stage = "updated"
        winners = set(n for n, _ in (st.session_state.best_team_a if win_team == "A" else st.session_state.best_team_b))

        updated_players = []
        for (n, r) in st.session_state.players:
            if str(n).strip() != "" and n in winners:
                updated_players.append((n, round(float(r) * float(multiplier))))
            else:
                updated_players.append((n, r))

        # 1) players を更新
        st.session_state.players = updated_players

        # 2) ウィジェットの状態も同期（ここが重要）
        for i in range(10):
            try:
                st.session_state[f"rate_{i}"] = int(updated_players[i][1])
            except Exception:
                st.session_state[f"rate_{i}"] = 0

        st.success("✅ レートを更新しました！ 入力欄にも反映されます。")
        st.rerun()
