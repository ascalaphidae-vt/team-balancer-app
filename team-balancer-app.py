# -*- coding: utf-8 -*-
# Streamlit app: スプラ3オートバランス！ by あすとらふぃーだ
# 改良点:
# 1) 日本語入力しやすいように、全体フォーム(st.form)を廃止
# 2) Enterキーで再実行されても入力が消えないように、各入力を session_state に即時保存
# 3) 一括入力・個別入力・チーム分け・レート更新を安定動作に整理

import re
import itertools
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

X_URL = "https://x.com/Ascalaphidae"

st.set_page_config(page_title="スプラ3オートバランス！", layout="wide")

# =========================
# セッション変数 初期化
# =========================
if "stage" not in st.session_state:
    # start -> 入力中
    # assigned_done -> チーム表示中
    # updated -> レート更新後
    st.session_state.stage = "start"

if "players" not in st.session_state:
    st.session_state.players = [("", 2000) for _ in range(10)]

if "participate" not in st.session_state:
    st.session_state.participate = [False for _ in range(10)]

if "bulk_input" not in st.session_state:
    st.session_state.bulk_input = ""

if "best_team_a" not in st.session_state:
    st.session_state.best_team_a = []

if "best_team_b" not in st.session_state:
    st.session_state.best_team_b = []

if "last_diff" not in st.session_state:
    st.session_state.last_diff = None

if "win_team" not in st.session_state:
    st.session_state.win_team = "A"

if "multiplier" not in st.session_state:
    st.session_state.multiplier = 1.03

# 各ウィジェット用の初期値を session_state に展開
for i in range(10):
    name_key = f"name_{i}"
    rate_key = f"rate_{i}"
    part_key = f"part_{i}"

    if name_key not in st.session_state:
        st.session_state[name_key] = st.session_state.players[i][0]
    if rate_key not in st.session_state:
        st.session_state[rate_key] = int(st.session_state.players[i][1])
    if part_key not in st.session_state:
        st.session_state[part_key] = st.session_state.participate[i]


# =========================
# 補助関数
# =========================
def sync_player_from_widgets(index: int):
    """各入力欄の値を players / participate に即時反映"""
    name = st.session_state.get(f"name_{index}", "")
    rate = int(st.session_state.get(f"rate_{index}", 0))
    part = bool(st.session_state.get(f"part_{index}", False))

    st.session_state.players[index] = (name, rate)
    st.session_state.participate[index] = part


def sync_all_players_from_widgets():
    """全プレイヤー分をまとめて同期"""
    for idx in range(10):
        sync_player_from_widgets(idx)


def load_widgets_from_players():
    """players / participate の内容を各入力欄へ戻す"""
    for idx in range(10):
        st.session_state[f"name_{idx}"] = st.session_state.players[idx][0]
        st.session_state[f"rate_{idx}"] = int(st.session_state.players[idx][1])
        st.session_state[f"part_{idx}"] = st.session_state.participate[idx]


def clear_team_result():
    st.session_state.best_team_a = []
    st.session_state.best_team_b = []
    st.session_state.last_diff = None


def reset_all():
    st.session_state.players = [("", 2000) for _ in range(10)]
    st.session_state.participate = [False for _ in range(10)]
    st.session_state.bulk_input = ""
    st.session_state.stage = "start"
    st.session_state.win_team = "A"
    st.session_state.multiplier = 1.03
    clear_team_result()
    load_widgets_from_players()


def parse_and_apply_bulk():
    raw = st.session_state.bulk_input or ""

    s = raw.replace("\n", ",")
    s = re.sub(r"[、；;]", ",", s)
    entries = [e.strip() for e in s.split(",") if e.strip()]

    applied = 0
    errors = []
    idx = 0

    # 一旦初期化
    st.session_state.players = [("", 2000) for _ in range(10)]
    st.session_state.participate = [False for _ in range(10)]

    for e in entries:
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

        rate_str = rate_str.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
        if not re.fullmatch(r"\d+", rate_str):
            errors.append(f"レートが数値ではありません: {e}")
            continue

        rate = max(0, int(rate_str))

        if idx < 10:
            st.session_state.players[idx] = (name, rate)
            st.session_state.participate[idx] = True
            idx += 1
            applied += 1
        else:
            errors.append(f"10枠を超えたためスキップ: {e}")

    clear_team_result()
    st.session_state.stage = "start"
    load_widgets_from_players()

    if applied > 0:
        st.success(f"✅ {applied}人を一括反映しました（参加ON）。")
    if errors:
        st.warning("⚠️ 次の項目は反映できませんでした：\n- " + "\n- ".join(errors))


def assign_teams(players_with_slot):
    """
    与えられた (slot, name, rate) のリストを2チームに最小差で分割。
    片方の人数は floor(n/2)。もう片方は n - floor(n/2)。
    """
    n = len(players_with_slot)
    if n < 2:
        return [], [], None

    k = n // 2
    min_diff = float("inf")
    best_a, best_b = [], []

    for combo in itertools.combinations(players_with_slot, k):
        team_a = list(combo)
        team_b = [p for p in players_with_slot if p not in team_a]
        sum_a = sum(p[2] for p in team_a)
        sum_b = sum(p[2] for p in team_b)
        diff = abs(sum_a - sum_b)

        if diff < min_diff:
            min_diff = diff
            best_a, best_b = team_a, team_b

    return best_a, best_b, min_diff


def run_team_assignment():
    sync_all_players_from_widgets()

    selected = [
        (i, n, r)
        for i, ((n, r), use) in enumerate(zip(st.session_state.players, st.session_state.participate))
        if use and str(n).strip() != ""
    ]
    n_sel = len(selected)

    if n_sel >= 9:
        clear_team_result()
        st.session_state.stage = "start"
        st.error("❌ 参加者が9人以上です。ゲームは最大8人までです。チェックを外して再実行してください。")
        return

    if n_sel < 2:
        clear_team_result()
        st.session_state.stage = "start"
        st.warning("⚠️ 2人以上選んでください。（名前が空欄だと無視されます）")
        return

    a, b, diff = assign_teams(selected)
    st.session_state.best_team_a = a
    st.session_state.best_team_b = b
    st.session_state.last_diff = diff
    st.session_state.stage = "assigned_done"
    st.success(f"💡 チーム分けしました！ 参加人数: {n_sel} / レート差: {diff}")


def update_ratings():
    sync_all_players_from_widgets()

    if not st.session_state.best_team_a or not st.session_state.best_team_b:
        st.warning("⚠️ 先にチーム分けをしてください。")
        return

    win_team = st.session_state.win_team
    multiplier = float(st.session_state.multiplier)

    winners_slots = {
        slot for (slot, _, _) in (
            st.session_state.best_team_a if win_team == "A" else st.session_state.best_team_b
        )
    }

    updated_players = list(st.session_state.players)
    for i, (n, r) in enumerate(st.session_state.players):
        if i in winners_slots and str(n).strip() != "":
            new_rate = int(round(float(r) * multiplier))
            updated_players[i] = (n, new_rate)

    st.session_state.players = updated_players
    load_widgets_from_players()
    st.session_state.stage = "updated"
    st.success("✅ レートを更新しました！ 入力欄の数値に反映されます。")


# =========================
# タイトル
# =========================
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
- Enterキーで再実行されても、入力内容は保持されます。
- **本アプリは非公式のファンメイドツールです**
""")

# =========================
# 一括入力 UI
# =========================
st.subheader("🧩 一括入力（プレイヤー名とレート）")
st.caption("例： あすふぃだ：2400, イシガケ：2000, ウスバキ：1800（全角/半角の：, 、 ; 改行などもOK）")

st.text_area(
    "形式：名前：レート をカンマ等で区切って入力（最大10人まで）",
    key="bulk_input",
    height=90,
    placeholder="あすふぃだ：2400, イシガケ：2000, ウスバキ：1800"
)

bulk_col1, bulk_col2 = st.columns([1, 1])
with bulk_col1:
    if st.button("反映", type="primary", use_container_width=True):
        parse_and_apply_bulk()
with bulk_col2:
    if st.button("🔄 入力をリセット", use_container_width=True):
        reset_all()
        st.rerun()

# =========================
# 個別入力フォーム相当
# =========================
st.subheader("🦑 プレイヤー情報の入力（個別） 🐙")
st.markdown("各プレイヤーの名前・レート・参加可否を調整してください。")

cols = st.columns(10)
for i in range(10):
    with cols[i]:
        st.markdown(f"**枠{i+1}**")

        st.text_input(
            f"名前{i+1}",
            key=f"name_{i}",
            on_change=sync_player_from_widgets,
            args=(i,),
        )

        st.number_input(
            f"レート{i+1}",
            min_value=0,
            step=50,
            key=f"rate_{i}",
            on_change=sync_player_from_widgets,
            args=(i,),
        )

        st.checkbox(
            "参加する",
            key=f"part_{i}",
            on_change=sync_player_from_widgets,
            args=(i,),
        )

st.markdown("")

action_col1, action_col2 = st.columns([2, 3])
with action_col1:
    if st.button("✅ チームを分ける", type="primary", use_container_width=True):
        run_team_assignment()

# =========================
# 状況に応じた画像
# =========================
if st.session_state.stage in ("start", "updated"):
    img_url = "https://cdn.discordapp.com/attachments/1291365679429189632/1362413372217364784/1.png?ex=68024dd4&is=6800fc54&hm=12d406f6e7bbda55e86f2fcbf700164ad03b8ce1142bd1766d449d383f2cf7a7&"
elif st.session_state.stage == "assigned_done":
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
# チーム表示
# =========================
if st.session_state.best_team_a and st.session_state.best_team_b:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🟦 チームA")
        df_a = pd.DataFrame(
            [(n, r) for (_, n, r) in st.session_state.best_team_a],
            columns=["名前", "レート"]
        )
        st.dataframe(df_a, use_container_width=True)
        st.markdown(f"**合計パワー：{int(sum(r for (_, _, r) in st.session_state.best_team_a))}**")

    with col2:
        st.markdown("### 🟨 チームB")
        df_b = pd.DataFrame(
            [(n, r) for (_, n, r) in st.session_state.best_team_b],
            columns=["名前", "レート"]
        )
        st.dataframe(df_b, use_container_width=True)
        st.markdown(f"**合計パワー：{int(sum(r for (_, _, r) in st.session_state.best_team_b))}**")

    if st.session_state.last_diff is not None:
        st.caption(f"レート差：{st.session_state.last_diff}")

    st.divider()
    st.subheader("🏆 勝利チームのレート更新")

    st.radio(
        "どちらのチームが勝ちましたか？",
        ["A", "B"],
        key="win_team",
        horizontal=True
    )

    st.number_input(
        "更新倍率（例：1.03 = 3%加算）",
        min_value=0.0,
        step=0.01,
        key="multiplier"
    )

    if st.button("📈 レートを更新する"):
        update_ratings()