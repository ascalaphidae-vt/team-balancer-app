# -*- coding: utf-8 -*-
# Streamlit app: スプラ3オートバランス！ by あすとらふぃーだ
# 改良点:
# 1) 個別入力をフォーム化し、日本語変換中の再実行を防止
# 2) Enterキーで確定しても入力内容を保持
# 3) レート更新後の StreamlitAPIException を回避
# 4) 更新倍率のデフォルト値を 1.03 に固定
# 5) 同じ対戦結果へのレート重複適用を防止

import base64
import itertools
import mimetypes
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

X_URL = "https://x.com/Ascalaphidae"
YOUTUBE_URL = "https://www.youtube.com/@%E3%81%82%E3%81%99%E3%81%A8%E3%82%89%E3%81%B5%E3%81%83%E3%83%BC%E3%81%A0"

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

st.set_page_config(page_title="スプラ3オートバランス！", layout="wide")

# =========================
# CSS
# =========================
st.markdown(
    """
    <style>
    :root {
        --dark-bg: #050609;
        --dark-panel: #0d1016;
        --dark-panel-2: #151924;
        --neon-cyan: #6ee7f2;
        --soft-pink: #ff9dca;
        --soft-lime: #d8ff8f;
        --text-main: #f7f4fb;
        --text-muted: #b9b4c4;
        --line: rgba(110, 231, 242, 0.28);
    }

    html, body, [class*="css"] {
        font-family:
            "Zen Maru Gothic",
            "Hiragino Maru Gothic ProN",
            "Yu Gothic",
            "Meiryo",
            sans-serif;
    }

    .stApp {
        color: var(--text-main);
        background:
            radial-gradient(
                circle at 12% 4%,
                rgba(255, 157, 202, 0.11),
                transparent 27rem
            ),
            radial-gradient(
                circle at 88% 18%,
                rgba(110, 231, 242, 0.10),
                transparent 30rem
            ),
            radial-gradient(
                circle at 65% 90%,
                rgba(216, 255, 143, 0.06),
                transparent 26rem
            ),
            linear-gradient(145deg, #030407 0%, #080a0f 48%, #050609 100%);
    }

    [data-testid="stHeader"] {
        background: rgba(5, 6, 9, 0.72);
        backdrop-filter: blur(12px);
    }

    [data-testid="stMainBlockContainer"] {
        max-width: 1540px;
        padding-top: 4.5rem;
    }

    h1, h2, h3 {
        color: var(--text-main);
        letter-spacing: 0.025em;
        text-shadow:
            0 0 12px rgba(110, 231, 242, 0.30),
            0 0 24px rgba(255, 157, 202, 0.14);
    }

    h1 {
        background: linear-gradient(
            90deg,
            var(--soft-pink),
            var(--text-main) 42%,
            var(--neon-cyan)
        );
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    h2::after, h3::after {
        content: "";
        display: block;
        width: 4.5rem;
        height: 2px;
        margin-top: 0.45rem;
        border-radius: 999px;
        background: linear-gradient(
            90deg,
            var(--soft-pink),
            var(--neon-cyan),
            transparent
        );
        box-shadow: 0 0 10px rgba(110, 231, 242, 0.55);
    }

    a {
        color: var(--neon-cyan) !important;
        text-decoration-color: rgba(255, 157, 202, 0.65) !important;
    }

    hr {
        border-color: transparent !important;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 157, 202, 0.55),
            rgba(110, 231, 242, 0.55),
            transparent
        ) !important;
        height: 1px !important;
    }

    [data-testid="stCaptionContainer"],
    [data-testid="stMarkdownContainer"] small {
        color: var(--text-muted);
    }

    [data-testid="stTextArea"] textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {
        color: var(--text-main);
        background: rgba(13, 16, 22, 0.94);
        border: 1px solid rgba(110, 231, 242, 0.34);
        border-radius: 13px;
        box-shadow:
            inset 0 0 18px rgba(110, 231, 242, 0.035),
            0 0 0 rgba(110, 231, 242, 0);
        transition:
            border-color 160ms ease,
            box-shadow 160ms ease,
            transform 160ms ease;
    }

    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: var(--neon-cyan);
        box-shadow:
            0 0 0 1px var(--neon-cyan),
            0 0 17px rgba(110, 231, 242, 0.24),
            0 0 28px rgba(255, 157, 202, 0.08);
    }

    [data-testid="stTextArea"] textarea::placeholder,
    [data-testid="stTextInput"] input::placeholder {
        color: #777384;
    }

    [data-testid="stForm"] {
        padding: 1.15rem;
        border: 1px solid var(--line);
        border-radius: 20px;
        background:
            linear-gradient(
                145deg,
                rgba(21, 25, 36, 0.82),
                rgba(9, 11, 16, 0.90)
            );
        box-shadow:
            0 14px 40px rgba(0, 0, 0, 0.35),
            0 0 25px rgba(110, 231, 242, 0.055);
    }

    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        min-height: 2.65rem;
        color: var(--text-main);
        font-weight: 700;
        letter-spacing: 0.035em;
        border: 1px solid rgba(110, 231, 242, 0.50);
        border-radius: 13px;
        background:
            linear-gradient(
                135deg,
                rgba(18, 25, 32, 0.98),
                rgba(24, 17, 29, 0.98)
            );
        box-shadow:
            inset 0 0 16px rgba(110, 231, 242, 0.06),
            0 0 14px rgba(110, 231, 242, 0.08);
        transition:
            transform 150ms ease,
            border-color 150ms ease,
            box-shadow 150ms ease;
    }

    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        color: #07090c;
        border-color: var(--soft-pink);
        background: linear-gradient(
            90deg,
            var(--soft-pink),
            var(--neon-cyan)
        );
        box-shadow:
            0 0 18px rgba(255, 157, 202, 0.28),
            0 0 24px rgba(110, 231, 242, 0.20);
        transform: translateY(-1px);
    }

    .stButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] > button[kind="primary"] {
        color: #050609;
        border-color: rgba(216, 255, 143, 0.90);
        background: linear-gradient(
            90deg,
            var(--soft-pink),
            var(--neon-cyan) 58%,
            var(--soft-lime)
        );
        box-shadow:
            0 0 18px rgba(110, 231, 242, 0.17),
            0 0 25px rgba(255, 157, 202, 0.12);
    }

    [data-testid="stCheckbox"] svg,
    [data-testid="stRadio"] svg {
        color: var(--soft-lime);
        filter: drop-shadow(0 0 5px rgba(216, 255, 143, 0.42));
    }

    [data-testid="stCheckbox"] label:hover,
    [data-testid="stRadio"] label:hover {
        color: var(--soft-pink);
    }

    [data-testid="stAlert"] {
        color: var(--text-main);
        border: 1px solid rgba(110, 231, 242, 0.36);
        border-radius: 15px;
        background:
            linear-gradient(
                120deg,
                rgba(110, 231, 242, 0.10),
                rgba(255, 157, 202, 0.08),
                rgba(216, 255, 143, 0.06)
            );
        box-shadow: 0 0 22px rgba(110, 231, 242, 0.07);
    }

    [data-testid="stDataFrame"] {
        overflow: hidden;
        border: 1px solid rgba(255, 157, 202, 0.34);
        border-radius: 16px;
        background: var(--dark-panel);
        box-shadow:
            0 12px 28px rgba(0, 0, 0, 0.30),
            0 0 18px rgba(255, 157, 202, 0.06);
    }

    [data-testid="stNumberInput"] button {
        color: var(--neon-cyan);
        background: rgba(110, 231, 242, 0.06);
        border-color: rgba(110, 231, 242, 0.22);
    }

    code {
        color: var(--soft-lime) !important;
        background: rgba(216, 255, 143, 0.08) !important;
        border: 1px solid rgba(216, 255, 143, 0.18);
        border-radius: 6px;
    }

    ::selection {
        color: #050609;
        background: var(--soft-pink);
    }

    @media (max-width: 700px) {
        [data-testid="stMainBlockContainer"] {
            padding-top: 3.5rem;
        }

        [data-testid="stForm"] {
            padding: 0.75rem;
            border-radius: 15px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# セッション変数 初期化
# =========================
if "stage" not in st.session_state:
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

if "notice" not in st.session_state:
    st.session_state.notice = None

# players -> widget 反映が必要なときだけ True
if "sync_widgets_from_players" not in st.session_state:
    st.session_state.sync_widgets_from_players = True


# =========================
# 補助関数
# =========================
def image_to_data_uri(filename: str):
    image_path = ASSETS_DIR / filename
    if not image_path.is_file():
        return None

    mime_type, _ = mimetypes.guess_type(image_path.name)
    mime_type = mime_type or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def sync_player_from_widgets(index: int):
    name = st.session_state.get(f"name_{index}", "")
    rate = int(st.session_state.get(f"rate_{index}", 0))
    part = bool(st.session_state.get(f"part_{index}", False))

    st.session_state.players[index] = (name, rate)
    st.session_state.participate[index] = part


def sync_all_players_from_widgets():
    for idx in range(10):
        sync_player_from_widgets(idx)


def clear_team_result():
    st.session_state.best_team_a = []
    st.session_state.best_team_b = []
    st.session_state.last_diff = None


def request_widget_sync():
    st.session_state.sync_widgets_from_players = True


def apply_widget_sync_if_needed():
    """
    ウィジェット描画前にだけ players / participate の値を
    name_i / rate_i / part_i へ流し込む
    """
    if st.session_state.sync_widgets_from_players:
        for idx in range(10):
            st.session_state[f"name_{idx}"] = st.session_state.players[idx][0]
            st.session_state[f"rate_{idx}"] = int(st.session_state.players[idx][1])
            st.session_state[f"part_{idx}"] = st.session_state.participate[idx]

        st.session_state.sync_widgets_from_players = False


def reset_all():
    st.session_state.players = [("", 2000) for _ in range(10)]
    st.session_state.participate = [False for _ in range(10)]
    st.session_state.bulk_input = ""
    st.session_state.stage = "start"
    st.session_state.win_team = "A"
    st.session_state.multiplier = 1.03
    st.session_state.notice = None
    clear_team_result()
    request_widget_sync()


def parse_and_apply_bulk():
    raw = st.session_state.bulk_input or ""

    s = raw.replace("\n", ",")
    s = re.sub(r"[、；;]", ",", s)
    entries = [e.strip() for e in s.split(",") if e.strip()]

    applied = 0
    errors = []
    idx = 0

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
    request_widget_sync()

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
    st.session_state.stage = "updated"

    # 同じ試合結果を誤って複数回適用できないよう、結果を消す。
    clear_team_result()
    request_widget_sync()
    st.session_state.notice = "✅ レートを更新しました！ 入力欄の数値に反映されています。"
    st.rerun()


# =========================
# 描画前同期
# =========================
apply_widget_sync_if_needed()

if st.session_state.notice:
    st.success(st.session_state.notice)
    st.session_state.notice = None


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

### 🕹️ つかいかた
- 下の **「🧩 一括入力」** に `名前：レート, 名前：レート, ...` の形式で入れて **反映** を押すと、
  プレイヤー1から順に **名前** と **レート** が一括反映されます。
- 一括反映された枠は **参加する** が自動でONになります。不要な枠はOFFにしてください。
- 「✅ チームを分ける」を押すと、**参加ONかつ名前が入っている人だけ**でチーム分けします。
- 個別入力はフォーム内で行うため、日本語変換中に画面が再実行されにくくなっています。
- Enterキーで確定しても入力内容は保持されます。
- **本アプリは非公式のファンメイドツールです**
""")


# =========================
# 一括入力 UI
# =========================
st.subheader("🧩 一括入力（プレイヤー名とレート）")
st.caption("例： あすふぃだ：2630, イシガケ：2000, ウスバキ：1800（全角/半角の：, 、 ; 改行などもOK）")

st.text_area(
    "形式：名前：レート をカンマ等で区切って入力（最大10人まで）",
    key="bulk_input",
    height=90,
    placeholder="あすふぃだ：2630, イシガケ：2000, ウスバキ：1800"
)

bulk_col1, bulk_col2 = st.columns([1, 1])
with bulk_col1:
    if st.button("反映", type="primary", use_container_width=True):
        parse_and_apply_bulk()
        st.rerun()

with bulk_col2:
    st.button(
        "🔄 入力をリセット",
        use_container_width=True,
        on_click=reset_all,
    )


# =========================
# 個別入力
# =========================
st.subheader("🦑 プレイヤー情報の入力（個別） 🐙")
st.markdown("各プレイヤーの名前・レート・参加可否を調整し、最後にチーム分けを押してください。")

# フォーム内の編集では即時再実行されないため、日本語IMEの変換状態が保たれやすい。
with st.form("player_form", clear_on_submit=False):
    for row_start in range(0, 10, 5):
        cols = st.columns(5)
        for offset, col in enumerate(cols):
            i = row_start + offset
            with col:
                st.markdown(f"**枠{i+1}**")
                st.text_input(
                    f"名前{i+1}",
                    key=f"name_{i}",
                    placeholder="プレイヤー名",
                )
                st.number_input(
                    f"レート{i+1}",
                    min_value=0,
                    step=50,
                    key=f"rate_{i}",
                )
                st.checkbox(
                    "参加する",
                    key=f"part_{i}",
                )

    assign_submitted = st.form_submit_button(
        "✅ チームを分ける",
        type="primary",
        use_container_width=True,
    )

if assign_submitted:
    run_team_assignment()


# =========================
# 状況に応じた画像
# =========================
if st.session_state.stage in ("start", "updated"):
    img_url = image_to_data_uri("character_start.png")
elif st.session_state.stage == "assigned_done":
    img_url = image_to_data_uri("character_assigned.png")
else:
    img_url = None

if img_url:
    components.html(f"""
    <script>
    function confirmAndRedirect() {{
        if (confirm('あすとらふぃーだのチャンネルを表示する？')) {{
            window.open('{YOUTUBE_URL}', '_blank');
        }}
    }}
    </script>
    <div style='position: fixed; bottom: 1rem; right: 1rem; z-index: 5;'>
        <img src='{img_url}' width='170' style='opacity: 0.85; border-radius: 10px; cursor: pointer;' onclick='confirmAndRedirect()'>
    </div>
    """, height=260)
else:
    st.caption("画像を表示できません。assetsフォルダと画像ファイル名を確認してください。")


# =========================
# チーム表示
# =========================
if st.session_state.best_team_a and st.session_state.best_team_b:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🟩 チームA")
        df_a = pd.DataFrame(
            [(n, r) for (_, n, r) in st.session_state.best_team_a],
            columns=["名前", "レート"]
        )
        st.dataframe(df_a, use_container_width=True)
        st.markdown(f"**合計パワー：{int(sum(r for (_, _, r) in st.session_state.best_team_a))}**")

    with col2:
        st.markdown("### 🟥 チームB")
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
        value=float(st.session_state.multiplier),
        step=0.01,
        key="multiplier"
    )

    if st.button("📈 レートを更新する"):
        update_ratings()
