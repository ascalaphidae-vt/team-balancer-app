
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import itertools

st.set_page_config(page_title="スプラ3オートバランス！", layout="wide")

# --- ステータス管理用セッション変数 ---
if "stage" not in st.session_state:
    st.session_state.stage = "start"  # start, assigned, updated

st.title("🎮 スプラ3オートバランス！byあすとらふぃーだ")
st.markdown("""
ゲームのレートに応じて最適なチーム分けを行い、勝利チームのレートを更新できます ✨

---

### 🕹️ つかいかた

1. **参加するプレイヤー名**と、**だいたいのパワー（レート）**を入力して、
   「✅ チームを分ける」を押すと、画面下にチーム編成が表示されます。

2. できあがったチームで対戦したあと、**勝ったチームを選んで「📈 レートを更新する」**を押してください。
   勝利チームのレートに少しだけボーナスが加算されます。

3. そのまま「✅ チームを分ける」をもう一度押せば、**前回の結果を反映した新しいチーム分け**ができます！
""")

# ========== ① 入力枠を10人に拡張 / ② 参加チェックボックスを追加 ==========
if "players" not in st.session_state:
    # (name, rate) を10枠まで保持
    st.session_state.players = [("", 2000) for _ in range(10)]
if "participate" not in st.session_state:
    # 参加可否チェック（初期値は False にしておく。名前を入れた人だけONでもOK）
    st.session_state.participate = [False for _ in range(10)]

# --- プレイヤー入力フォーム + リセットボタン ---
st.subheader("🦑プレイヤー情報の入力🐙")
st.markdown("各プレイヤーの名前と現在のレート、参加可否を入力してください")

with st.form(key="player_form"):
    reset_col, form_col = st.columns([1, 5])
    with reset_col:
        if st.form_submit_button("🔄 入力をリセット"):
            st.session_state.players = [("", 2000) for _ in range(10)]
            st.session_state.participate = [False for _ in range(10)]
            st.session_state.stage = "start"
            if "best_team_a" in st.session_state: del st.session_state["best_team_a"]
            if "best_team_b" in st.session_state: del st.session_state["best_team_b"]
            st.rerun()

    # 10列を横並び（画面幅が狭いと折り返されます）
    cols = st.columns([1]*10)
    for i in range(10):
        with cols[i]:
            st.markdown(f"**枠{i+1}**")
            name = st.text_input(f"名前{i+1}", value=st.session_state.players[i][0], key=f"name_{i}")
            rate = st.number_input(f"レート{i+1}", min_value=0, value=st.session_state.players[i][1], step=50, key=f"rate_{i}")
            part = st.checkbox("参加する", value=st.session_state.participate[i], key=f"part_{i}")
            # セッションに反映
            st.session_state.players[i] = (name, rate)
            st.session_state.participate[i] = part

    submit = st.form_submit_button("✅ チームを分ける")
    if submit:
        st.session_state.stage = "assigned"

# --- チーム分けロジック ---
def assign_teams(players_list):
    """与えられた (name, rate) のリストを2チームに最小差で分割"""
    n = len(players_list)
    if n < 2:
        return [], [], None  # 2人未満は編成不可
    # ④ 7人以下でも動くよう、人数に応じてチームサイズを自動調整
    k = n // 2  # 片方のチーム人数（もう片方は n-k）
    min_diff = float('inf')
    best_a, best_b = [], []
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

# --- 入力確定後の処理 ---
if "best_team_a" in st.session_state and "best_team_b" in st.session_state and st.session_state.stage != "assigned":
    # 後段UIからのrerunで参照できるよう保持
    pass

if st.session_state.get("stage") == "assigned" and submit:
    # 参加チェックがONかつ名前が空でない人のみ抽出
    selected = [(n, r) for (n, r), use in zip(st.session_state.players, st.session_state.participate) if use and str(n).strip() != ""]
    n_sel = len(selected)

    # ③ 参加人数が9人以上（=ゲーム最大8人超過）の場合はエラー表示して復旧
    if n_sel >= 9:
        st.session_state.stage = "start"
        if "best_team_a" in st.session_state: del st.session_state["best_team_a"]
        if "best_team_b" in st.session_state: del st.session_state["best_team_b"]
        st.error("❌ 参加者が9人以上です。ゲームは最大8人までです。チェックを外すか入力を調整して、再度お試しください。")
    else:
        # 参加者が1人以下の場合は編成できない
        if n_sel < 2:
            st.warning("⚠️ 2人以上選んでください。（名前が空欄だと無視されます）")
        else:
            # ④ 7人以下でも動作（上の assign_teams が自動で分割）
            a, b, diff = assign_teams(selected)
            st.session_state.best_team_a = a
            st.session_state.best_team_b = b
            st.session_state.stage = "assigned_done"
            if diff is not None:
                st.success(f"💡 チーム分けしました！ レート差: {diff}")

# --- 状況に応じた画像表示 ---
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

# --- チーム表示
if "best_team_a" in st.session_state and "best_team_b" in st.session_state:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🟦 チームA")
        df_a = pd.DataFrame(st.session_state.best_team_a, columns=["名前", "レート"])
        st.dataframe(df_a, use_container_width=True)
        st.markdown(f"**合計パワー：{df_a['レート'].sum()}**")
    with col2:
        st.markdown("### 🟨 チームB")
        df_b = pd.DataFrame(st.session_state.best_team_b, columns=["名前", "レート"])
        st.dataframe(df_b, use_container_width=True)
        st.markdown(f"**合計パワー：{df_b['レート'].sum()}**")

    # --- 勝利チーム選択 & 倍率指定 ---
    st.subheader("🏆 勝利チームのレート更新")
    win_team = st.radio("どちらのチームが勝ちましたか？", ["A", "B"], horizontal=True)
    multiplier = st.number_input("更新倍率（例：1.03 = 3%加算）", value=1.03, step=0.01)

    if st.button("📈 レートを更新する"):
        st.session_state.stage = "updated"

        # 勝利チームのメンバー名セット
        winners = set(n for n, _ in (st.session_state.best_team_a if win_team == "A" else st.session_state.best_team_b))

        # すべての枠（10枠）について、勝者に該当する人だけレートを更新し、それ以外はそのまま
        updated_players = []
        for (n, r) in st.session_state.players:
            if str(n).strip() != "" and n in winners:
                updated_players.append((n, round(r * multiplier)))
            else:
                updated_players.append((n, r))

        st.session_state.players = updated_players

        st.success("✅ レートを更新しました！ 入力欄にも反映されます")
        components.html("""
        <script>
            const topElement = document.querySelector('body');
            if (topElement) topElement.scrollIntoView({ behavior: 'smooth' });
        </script>
        """, height=0)
        st.rerun()
