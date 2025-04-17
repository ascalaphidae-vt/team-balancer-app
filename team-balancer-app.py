import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import itertools

st.set_page_config(page_title="スプラ3オートバランス！", layout="wide")

# --- ステータス管理用セッション変数 ---
if "stage" not in st.session_state:
    st.session_state.stage = "start"  # start, assigned, updated

st.title("🎮 スプラ3オートバランス！byあすとらふぃーだ")
st.markdown("ゲームのレートに応じて最適なチーム分けを行い、勝利チームのレートを更新できます ✨")

# --- セッション状態の初期化 ---
if "players" not in st.session_state:
    st.session_state.players = [("", 2000) for _ in range(8)]

# --- プレイヤー入力フォーム + リセットボタン ---
st.subheader("🦑プレイヤー情報の入力🐙")
st.markdown("各プレイヤーの名前と現在のレートを入力してください")

with st.form(key="player_form"):
    reset_col, form_col = st.columns([1, 5])
    with reset_col:
        if st.form_submit_button("🔄 入力をリセット"):
            st.session_state.players = [("", 2000) for _ in range(8)]
            st.rerun()
    cols = st.columns([1]*8)
    for i in range(8):
        with cols[i]:
            name = st.text_input(f"名前{i+1}", value=st.session_state.players[i][0], key=f"name_{i}")
            rate = st.number_input(f"レート{i+1}", min_value=0, value=st.session_state.players[i][1], step=50, key=f"rate_{i}")
            st.session_state.players[i] = (name, rate)
    submit = st.form_submit_button("✅ チームを分ける")
    if submit:
        st.session_state.stage = "assigned"

# --- チーム分けロジック ---
if submit:
    players = st.session_state.players
    min_diff = float('inf')
    best_team_a, best_team_b = [], []

    for combo in itertools.combinations(players, 4):
        team_a = list(combo)
        team_b = [p for p in players if p not in team_a]
        sum_a = sum(p[1] for p in team_a)
        sum_b = sum(p[1] for p in team_b)
        diff = abs(sum_a - sum_b)

        if diff < min_diff:
            min_diff = diff
            best_team_a, best_team_b = team_a, team_b

    st.session_state.best_team_a = best_team_a
    st.session_state.best_team_b = best_team_b

# --- チーム表示（この位置に画像も表示）

# --- 状況に応じた画像表示 ---
if st.session_state.stage == "start" or st.session_state.stage == "updated":
    img_url = "https://cdn.discordapp.com/attachments/1291365679429189632/1362413372217364784/1.png?ex=68024dd4&is=6800fc54&hm=12d406f6e7bbda55e86f2fcbf700164ad03b8ce1142bd1766d449d383f2cf7a7&"
elif st.session_state.stage == "assigned":
    img_url = "https://cdn.discordapp.com/attachments/1291365679429189632/1362413397353693184/2.png?ex=68024dda&is=6800fc5a&hm=7537e4ecb893d42b6d028bc267f8e53b701d7e3b021fc9ea4a66b92dbe323f14&"
else:
    img_url = ""

if img_url:
    components.html(f"""
    <script>
    function confirmAndRedirect() {
        if (confirm('あすとらふぃーだのチャンネルを表示する？')) {
            window.open('https://www.youtube.com/channel/UCjJbi4Fs5kZIRAVWvNBPOpA', '_blank');
        }
    }
    </script>
    <div style='position: absolute; bottom: 0; right: 1rem; z-index: 5;'>
        <img src='{img_url}' width='180' style='opacity: 0.85; border-radius: 10px; cursor: pointer;' onclick='confirmAndRedirect()'>
    </div>
    """, height=220)
if "best_team_a" in st.session_state and "best_team_b" in st.session_state:
    st.success(f"💡 チーム分けしました！レート差: {abs(sum(p[1] for p in st.session_state.best_team_a) - sum(p[1] for p in st.session_state.best_team_b))}")

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
    win_team = st.radio("どちらのチームが勝ちましたか？", ["A", "B"])
    multiplier = st.number_input("更新倍率（例：1.03 = 3%加算）", value=1.03, step=0.01)

    if st.button("📈 レートを更新する"):
        st.session_state.stage = "updated"
        if win_team == "A":
            updated = [(n, round(r * multiplier)) for n, r in st.session_state.best_team_a] + st.session_state.best_team_b
        else:
            updated = st.session_state.best_team_a + [(n, round(r * multiplier)) for n, r in st.session_state.best_team_b]

        # セッションのプレイヤーデータを更新
        st.session_state.players = updated

        # 再入力用のセッションデータのみ更新（UI更新せず、再読み込みで反映）
        # ウィジェット表示後の直接書き換えは禁止されているため rerun を使う
        st.success("✅ レートを更新しました！ 入力欄にも反映されます")
        st.rerun()

        st.success("✅ レートを更新しました！ 入力欄にも反映されています")
