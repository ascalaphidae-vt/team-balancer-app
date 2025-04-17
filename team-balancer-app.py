import streamlit as st
import pandas as pd
import itertools

st.set_page_config(page_title="チーム自動バランサー", layout="wide")

st.title("🎮 チーム自動バランサー")
st.markdown("ゲームのレートに応じて最適なチーム分けを行い、勝利チームのレートを更新できます ✨")

# --- セッション状態の初期化 ---
if "players" not in st.session_state:
    st.session_state.players = [("", 2000) for _ in range(8)]

# --- プレイヤー入力フォーム + リセットボタン ---
st.subheader("👥 プレイヤー情報の入力")
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

# --- チーム表示 ---
if "best_team_a" in st.session_state and "best_team_b" in st.session_state:
    st.success(f"💡 最適なチームが見つかりました！レート差: {abs(sum(p[1] for p in st.session_state.best_team_a) - sum(p[1] for p in st.session_state.best_team_b))}")

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
