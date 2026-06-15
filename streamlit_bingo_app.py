import copy
import hashlib
import html
import random
import unicodedata
from typing import Dict, Optional

import streamlit as st

st.set_page_config(page_title="スプラビンゴ", page_icon="🎯", layout="wide")

# =========================
# お題データ
# =========================
level1_topics = [
    'フデをつかって「勝つ」',
    'ストリンガーをつかって「勝つ」',
    'シューターをつかって「勝つ」',
    'ブラスターを「使う」',
    'ワイパーを「使う」',
    'スロッシャーをつかって「勝つ」',
    'ローラーをつかって「勝つ」',
    'スプラシューターでキルとアシスト合計5以上',
    '52ガロンで4デス以下',
    'わかばシューターで1000ポイント以上塗る',
    'N-ZAP85(黒ZAP)でSP4回以上使う',
    '1100ポイント以上塗る',
    'リザルトでキルかアシストを合計10以上',
    'リザルト5デス以下',
    '1試合でスペシャル5回以上つかう',
    'スペシャル発動中に試合がおわる',
    'サブウェポンで相手をたおす',
    'メインギアパワーをインク回復力アップのみにする',
    'メインギアパワーをサブ影響軽減のみにする',
    'メインギアパワーをスペシャル減少量ダウンのみにする',
    'ペナルティアップを付けたもみじシューターを「使う」',
    '逆境、イカニン、対物アップを同時に「使う」',
    'ダイナモ、リッター、エクスのいずれかを「使う」',
    'ハイドラ、キャンシェル、フルイドのいずれかを「使う」',
    'スパイガジェットソレーラかワイドローラーを「使う」',
    'クラッシュブラスターネオかガエンFFを「使う」',
    'カニタンクを使って１キル以上する',
    'テイオウイカを使って１試合で２キル以上する',
    '(スペシャル名)NO.1の表彰を得る',
    'ギア・スタートダッシュを付けて「勝つ」',
    'ギア・復活ペナルティアップを付けて「勝つ」',
    'ギア・受け身術を付けて「勝つ」',
    '相手４人全員にポイントセンサーをつける',
]

level2_topics = [
    'じゅくれんど☆１以下のブキを使う（ストーリー系不可）',
    '相手チームの誰よりも多いキルとアシスト数の合計',
    '相手チームの誰よりも少ないデス数',
    '相手チームの誰よりも多い塗りポイント',
    '相手チームの誰よりも多いSP使用回数',
    'キルとアシスト数の合計とデス数が同じ',
    'デス数とSP使用数が同じ',
    'キルとアシスト数の合計とSP使用数が同じ',
    'リッター系統でキルとアシスト合計5以上',
    'ダイナモローラー系統で4デス以下',
    'エクスプロッシャー系統で1000ポイント以上塗る',
    'ハイドラント系統でSP5回以上使う',
    'スパイガジェット系統でキルとアシスト合計8以上',
    'ラピッドブラスターエリート系統で2デス以下',
    'ケルビン525系統で800ポイント以上塗る',
    'プロモデラー系統でSP7回以上使う',
    'イグザミナー系統でキルかアシスト合計10以上',
    '30秒経過ごとに、残り試合時間をさけぶ',
    '14式竹筒銃系統で3デス以下',
    'LACT系統で1500ポイント以上塗る',
    'R-PEN系統でSP6回以上使う',
    'ラインマーカーでキルする',
    'カーリングボムでキルする',
    'トリプルトルネードでキルする',
    'ショクワンダーの突撃でキルする',
    'ウルトラハンコ投げでキルする',
    'フデかローラーでコロコロキルする',
    '注目された時間NO.1と塗りポイントNO.1の表彰を同時に得る',
    '塗りポイントNO.1とバトルNO.1の表彰を同時に得る',
    '注目された時間NO.1とバトルNO.1の表彰を同時に得る',
    '2人で同時にテイオウイカを使う',
    '2人で同時にカニタンクを使う',
    '2人で同時にウルトラハンコを使う',
    '2人で同時にホップソナーを使う',
    '2人で同時にスミナガシートを使う',
    'シェルターで「勝つ」',
    'チャージャーで「勝つ」',
    'スクイックリンβを「使う」',
    'パブロ・ヒューを「使う」',
    'H3リールガンDを「使う」',
    '「スプラトゥーンあるある」を試合中に発表',
    '「こんなスプラトゥーンはいやだ」を試合中に発表',
    'ソイチューバーカスタムを「使う」',
    'スピナーで「勝つ」',
    'マニューバーで「勝つ」',
    '残り試合1分で同時にナイスを押す',
    '視聴者リクエストのブキを使って勝つ',
    '試合終了間際にカーリングボムを投げ、ガッツポーズする',
]

level3_topics = [
    'キルとアシスト合計15回以上で「勝つ」',
    '1デス以下で「勝つ」',
    '1500ポイント以上塗って「勝つ」',
    'スペシャルを7回以上使って「勝つ」',
    'キルとアシスト数より多いデス数で「勝つ」',
    'トラップで１キル以上する',
    'アメフラシで１キル以上する',
    'スミナガシートで１キル以上する',
    'トライストリンガー系統で金表彰3つ',
    'キャンシェル系統で金表彰3つ',
    'オフロ無印でキルかアシスト10以上',
    'フィンセント無印で2デス以下',
    'Sブラ91で塗りポイント1000以上',
    '金ノーチラスでSP5回以上使う',
    '張替傘乙(和傘乙)を使って勝利する',
    'ボトルガイザーフォイルを使って勝利する',
    'イカニンでイカ速0のダイナモ冥を使って勝利する',
    'イカフローになる',
    'イカフローの相手を倒す',
    'JoyConでプレイする',
    'イカニンジャをつけて、試合中ござる口調',
    'リザルトでスコア（塗りも含む）に２の数字が３つ以上',
    'リザルトでスコア（塗りも含む）に１の数字が４つ以上',
    '試合中に食べ物名のプレイヤーを発見する',
    'ダイナモローラー系統で試合中20回数えながらタテ振りする',
    '塗りポイントNO.1と移動した距離NO.1の表彰を同時に得る',
    'バトルNO.1と耐えたダメージNO.1の表彰を同時に得る',
    '注目された時間NO.1とアシスト数NO.1の表彰を同時に得る',
    'H3Dで3点バーストキルをする',
    'ブキ選択画面で使った順の、最後のページにあるブキを使う',
    '一人が1試合中スペシャルを使わない',
    '一人が1試合中サブウェポンを使わない',
    'ウルトラチャクチをスーパージャンプ中に使ってキルをする',
    'エナスタを使うたびに、エナドリの名前を１つ言う(2回以上やる)',
    '2人で同時に並んでショクワンダーを使う',
    '2人で同時に並んでジェットパックを使う',
    '試合中に状況に適したスプラ豆知識を１つ言う',
    '勝敗演出(ダンス)中に味方のブキを4つ言い当てる',
    '勝敗演出(ダンス)中に相手のブキを4つ言い当てる',
    '試合中に何かを食べ、食レポする',
    '試合終了後に塗りポイントの下二けたが同じ数字',
]

level4_topics = [
    'スペースシューターでトドメNO.1を得る',
    'じゅくれんど☆０以下のブキを使って「勝つ」（ストーリー系不可）',
    'カーボンローラー無印でアシストNO.1を得る',
    'ジャイロオンかスティックのみ、普段と逆の方にする',
    'ジャイロとスティック感度-5にする',
    'Switch2のホームボタンを2度押しズーム（デフォルトの拡大率）にする',
    '試合中マップを開きっぱなしにする',
    'カニタンクの球体モードで1キル以上する',
    '試合開始時に大喜利のお題を聞き、試合中に答える',
    'スプラに関するダジャレを言う(重複不可)',
    'ビンゴプレイヤー同士でグータッチ',
    'ジムワイパーを使い、試合中事務的な口調にする',
    '試合中英語をつかわない',
    '試合中ジャンプしない',
    '試合中イカ状態にならない',
    '3キル3デス3スペシャルで「勝つ」',
    '●●をたおした‼が3つ表示されているときにスクショを撮る',
    'フルイドVカスタムでピチュンキルをする',
    'デンタルワイパーミントで1振りで同時に2人斬る',
    'キルをする前に相手プレイヤー名を当ててキルをする（最低３回）',
    'サメライドを使うたびに、実際のサメの種類を１つ言う(3回以上やる)',
    'キルかアシスト合計1回以下で「勝つ」',
    '塗りポイント400ポイント以下で「勝つ」',
    'マッチメイク中に自分以外のビンゴプレイヤーのイラストを描く',
    'ビンゴプレイヤーの仲間が相手と同時に映っているタイミングでスクショ',
    'ポップソナーをぶつけて相手を倒す',
    'ボトルガイザーの長射程モードを使わずに試合で勝つ',
    'Sブラスターの長射程モードを使わずに試合で勝つ',
]

center_topics = [
    'ビンゴプレイヤーで同じブキにそろえる',
    '互いの持ちブキを交換',
    '互いのいつものギア(見た目)を交換',
    'ビンゴプレイヤーでおそろいのギアにする',
    '1人1つ以上お題を同時に達成する',
    '前の試合で相手が使っていたブキの1つをつかう',
    '連勝する',
]

BOARD_OPTIONS = ['9マスビンゴシート', '25マスビンゴシート']
COLOR_MAP = {
    'pink': '#ffd7e2',
    'green': '#daf5da',
    'blue': '#dceeff',
    'lightyellow': '#fff7c8',
    'lightpurple': '#ead9ff',
    'white': '#ffffff',
    'black': '#111111',
}
COLOR_LABELS = {
    'pink': 'Lv1枠',
    'green': 'Lv2枠',
    'blue': 'Lv3枠',
    'lightpurple': 'Lv4枠',
    'lightyellow': '中央枠',
    'black': 'クリア済み',
}

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 1.0rem;
        max-width: 1480px;
    }
    .app-title {
        font-size: 2rem;
        font-weight: 700;
        margin-top: 0.1rem;
        margin-bottom: 0.2rem;
        line-height: 1.25;
    }
    .app-sub {
        color: #666;
        margin-bottom: 1.0rem;
    }
    .seed-note {
        font-size: 0.92rem;
        color: #666;
        margin-top: -0.2rem;
        margin-bottom: 0.8rem;
    }
    .bingo-cell {
        border: 1px solid rgba(49, 51, 63, 0.14);
        border-radius: 12px;
        padding: 0.42rem 0.48rem;
        min-height: 96px;
        margin-bottom: 0.24rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        overflow: hidden;
    }
    .bingo-cell.small-board {
        min-height: 104px;
        padding: 0.5rem 0.56rem;
    }
    .bingo-cell.small-board .bingo-pos {
        font-size: 0.8rem;
        margin-bottom: 0.24rem;
    }
    .bingo-cell.small-board .bingo-topic {
        font-size: 0.98rem;
        line-height: 1.34;
    }
    .bingo-cell.small-board .done-badge {
        font-size: 0.78rem;
        margin-top: 0.5rem;
    }
    .bingo-pos {
        font-size: 0.68rem;
        font-weight: 700;
        color: #222222;
        opacity: 0.9;
        margin-bottom: 0.18rem;
    }
    .bingo-topic {
        font-size: 0.76rem;
        line-height: 1.24;
        color: #111111;
        word-break: break-word;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
        font-weight: 600;
    }
    .done-badge {
        display: inline-block;
        padding: 0.14rem 0.42rem;
        border-radius: 999px;
        background: rgba(0, 0, 0, 0.08);
        color: #111111;
        font-size: 0.66rem;
        font-weight: 700;
        margin-top: 0.4rem;
    }
    .legend-chip {
        display: inline-block;
        padding: 0.22rem 0.56rem;
        border-radius: 999px;
        margin: 0.1rem 0.18rem 0.1rem 0;
        font-size: 0.78rem;
        border: 1px solid rgba(49, 51, 63, 0.12);
        color: #111111;
        font-weight: 600;
    }
    div[data-testid="column"] {
        padding-left: 0.14rem;
        padding-right: 0.14rem;
    }
    div[data-testid="stButton"] > button {
        padding-top: 0.28rem;
        padding-bottom: 0.28rem;
        font-size: 0.88rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    if 'bingo_card' not in st.session_state:
        st.session_state.bingo_card = None
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'current_level' not in st.session_state:
        st.session_state.current_level = 1
    if 'last_seed_text' not in st.session_state:
        st.session_state.last_seed_text = ""
    if 'board_mode' not in st.session_state:
        st.session_state.board_mode = '9マスビンゴシート'
    if 'grid_size' not in st.session_state:
        st.session_state.grid_size = 3
    if 'memo_text' not in st.session_state:
        st.session_state.memo_text = ''


def text_to_seed(text: str, max_value: Optional[int] = None) -> int:
    normalized = unicodedata.normalize('NFC', text)
    digest = hashlib.sha256(normalized.encode('utf-8')).digest()
    seed = int.from_bytes(digest[:8], byteorder='big', signed=False)
    if max_value is not None:
        if max_value <= 0:
            raise ValueError('max_value は 1 以上である必要があります。')
        seed %= max_value
    return seed


def make_random_from_text(text: str) -> random.Random:
    return random.Random(text_to_seed(text))


def get_board_spec(board_mode: str) -> tuple[list[str], list[str], str, int]:
    if board_mode == '9マスビンゴシート':
        return ['1', '2', '3'], ['A', 'B', 'C'], 'B-2', 3
    return ['1', '2', '3', '4', '5'], ['A', 'B', 'C', 'D', 'E'], 'C-3', 5


def build_topics_with_colors_25(level: int, rng: random.Random) -> tuple[list[tuple[str, str]], tuple[str, str]]:
    if level == 1:
        topics = rng.sample(level1_topics, 14) + rng.sample(level2_topics, 10)
        colors = ['pink'] * 14 + ['green'] * 10
    elif level == 2:
        topics = rng.sample(level1_topics, 10) + rng.sample(level2_topics, 12) + rng.sample(level3_topics, 2)
        colors = ['pink'] * 10 + ['green'] * 12 + ['blue'] * 2
    elif level == 3:
        topics = rng.sample(level1_topics, 7) + rng.sample(level2_topics, 13) + rng.sample(level3_topics, 3) + rng.sample(level4_topics, 1)
        colors = ['pink'] * 7 + ['green'] * 13 + ['blue'] * 3 + ['lightpurple'] * 1
    elif level == 4:
        topics = rng.sample(level2_topics, 10) + rng.sample(level3_topics, 12) + rng.sample(level4_topics, 2)
        colors = ['green'] * 10 + ['blue'] * 12 + ['lightpurple'] * 2
    elif level == 5:
        topics = rng.sample(level2_topics, 6) + rng.sample(level3_topics, 12) + rng.sample(level4_topics, 6)
        colors = ['green'] * 6 + ['blue'] * 12 + ['lightpurple'] * 6
    else:
        raise ValueError('レベルは1〜5のみ対応です。')

    combined = list(zip(topics, colors))
    rng.shuffle(combined)
    center = (rng.choice(center_topics), 'lightyellow')
    return combined, center


def build_topics_with_colors_9(level: int, rng: random.Random) -> tuple[list[tuple[str, str]], tuple[str, str]]:
    if level == 1:
        remaining = [(t, 'pink') for t in rng.sample(level1_topics, 5)] + [(t, 'green') for t in rng.sample(level2_topics, 3)]
        center = (rng.choice(center_topics), 'lightyellow')
    elif level == 2:
        remaining = (
            [(t, 'pink') for t in rng.sample(level1_topics, 3)]
            + [(t, 'green') for t in rng.sample(level2_topics, 4)]
            + [(t, 'blue') for t in rng.sample(level3_topics, 1)]
        )
        center = (rng.choice(center_topics), 'lightyellow')
    elif level == 3:
        remaining = (
            [(t, 'pink') for t in rng.sample(level1_topics, 1)]
            + [(t, 'green') for t in rng.sample(level2_topics, 2)]
            + [(t, 'blue') for t in rng.sample(level3_topics, 4)]
            + [(t, 'lightpurple') for t in rng.sample(level4_topics, 1)]
        )
        center = (rng.choice(center_topics), 'lightyellow')
    elif level == 4:
        remaining = (
            [(t, 'green') for t in rng.sample(level2_topics, 2)]
            + [(t, 'blue') for t in rng.sample(level3_topics, 4)]
            + [(t, 'lightpurple') for t in rng.sample(level4_topics, 2)]
        )
        center = (rng.choice(level3_topics), 'blue')
    elif level == 5:
        remaining = (
            [(t, 'green') for t in rng.sample(level2_topics, 1)]
            + [(t, 'blue') for t in rng.sample(level3_topics, 3)]
            + [(t, 'lightpurple') for t in rng.sample(level4_topics, 4)]
        )
        center = (rng.choice(level4_topics), 'lightpurple')
    else:
        raise ValueError('レベルは1〜5のみ対応です。')

    rng.shuffle(remaining)
    return remaining, center


def generate_bingo_card(level: int, seed_text: str, board_mode: str) -> tuple[Dict[str, Dict[str, str]], int]:
    rows, cols, center_pos, grid_size = get_board_spec(board_mode)
    rng = make_random_from_text(f'mode:{board_mode}|level:{level}|seed:{seed_text}')

    if board_mode == '9マスビンゴシート':
        remaining, center = build_topics_with_colors_9(level, rng)
    else:
        remaining, center = build_topics_with_colors_25(level, rng)

    bingo_card: Dict[str, Dict[str, str]] = {}
    index = 0
    for row in rows:
        for col in cols:
            position = f'{col}-{row}'
            if position == center_pos:
                topic, color = center
            else:
                topic, color = remaining[index]
                index += 1
            bingo_card[position] = {'topic': topic, 'color': color, 'cleared': False}

    return bingo_card, grid_size


def push_history() -> None:
    if st.session_state.bingo_card is None:
        return
    st.session_state.history.append(copy.deepcopy(st.session_state.bingo_card))
    if len(st.session_state.history) > 5:
        st.session_state.history.pop(0)


def clear_cell(position: str) -> None:
    if st.session_state.bingo_card is None:
        return
    cell = st.session_state.bingo_card[position]
    if cell['cleared']:
        return
    push_history()
    cell['topic'] = 'Clear!!'
    cell['color'] = 'black'
    cell['cleared'] = True


def undo() -> None:
    if st.session_state.history:
        st.session_state.bingo_card = st.session_state.history.pop()


def count_cleared(card: Dict[str, Dict[str, str]]) -> int:
    return sum(1 for cell in card.values() if cell.get('cleared'))


def render_legend() -> None:
    chips = []
    for key in ['pink', 'green', 'blue', 'lightpurple', 'lightyellow', 'black']:
        chips.append(
            f"<span class='legend-chip' style='background:{COLOR_MAP[key]}; color:{'#ffffff' if key == 'black' else '#111111'}'>{html.escape(COLOR_LABELS[key])}</span>"
        )
    st.markdown(''.join(chips), unsafe_allow_html=True)


def render_cell(position: str, cell: Dict[str, str], is_small_board: bool) -> None:
    bg = COLOR_MAP.get(cell['color'], '#ffffff')
    body = html.escape(cell['topic']).replace('\n', '<br>')
    is_cleared = cell.get('cleared')
    text_color = '#ffffff' if is_cleared else '#111111'
    pos_color = '#ffffff' if is_cleared else '#222222'
    badge_bg = 'rgba(255, 255, 255, 0.18)' if is_cleared else 'rgba(0, 0, 0, 0.08)'
    badge_color = '#ffffff' if is_cleared else '#111111'
    done_badge = f"<div class='done-badge' style='background:{badge_bg}; color:{badge_color};'>クリア済み</div>" if is_cleared else ''
    extra_class = 'small-board' if is_small_board else ''
    st.markdown(
        f"""
        <div class="bingo-cell {extra_class}" style="background:{bg};">
            <div>
                <div class="bingo-pos" style="color:{pos_color};">{position}</div>
                <div class="bingo-topic" style="color:{text_color};">{body}</div>
            </div>
            {done_badge}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if is_cleared:
        st.button('クリア済み', key=f'done_{position}', disabled=True, use_container_width=True)
    else:
        if st.button(f'{position} をクリア', key=f'clear_{position}', use_container_width=True):
            clear_cell(position)
            st.rerun()


init_state()

st.markdown("<div class='app-title'>🎯 スプラビンゴ</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='app-sub'>9マス版と25マス版を切り替えて、達成したマスを手動でクリアしていく用のStreamlit版です。</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header('設定')
    board_mode = st.radio('シートサイズ', BOARD_OPTIONS, index=0 if st.session_state.board_mode == '9マスビンゴシート' else 1)
    selected_level = st.radio('レベルを選ぶ', [1, 2, 3, 4, 5], index=st.session_state.current_level - 1, horizontal=False)
    seed_text = st.text_input('シード文字列', value=st.session_state.last_seed_text)
    st.caption('同じサイズ・同じレベル・同じ文字列なら同じビンゴシートになります。')

    if st.button('新しいビンゴを生成', use_container_width=True):
        st.session_state.current_level = selected_level
        st.session_state.last_seed_text = seed_text
        st.session_state.board_mode = board_mode
        st.session_state.bingo_card, st.session_state.grid_size = generate_bingo_card(selected_level, seed_text, board_mode)
        st.session_state.history = []
        st.rerun()

    undo_disabled = len(st.session_state.history) == 0
    if st.button('1手もどす', use_container_width=True, disabled=undo_disabled):
        undo()
        st.rerun()

    if st.session_state.bingo_card is not None:
        total_cells = len(st.session_state.bingo_card)
        cleared = count_cleared(st.session_state.bingo_card)
        st.metric('クリア済みマス', f'{cleared} / {total_cells}')
        st.caption(f'戻せる履歴: {len(st.session_state.history)} / 5')
        shown_seed = st.session_state.last_seed_text if st.session_state.last_seed_text != '' else '（空欄）'
        st.caption(f'現在のシード: {shown_seed}')

    st.divider()
    st.write('あそびかた')
    st.caption('1. シートサイズ・レベル・シード文字列を決めて新規生成してください')
    st.caption('2. 同じ条件なら同じ盤面になります')
    st.caption('3. 試合後、達成したマスぶんだけ「◯-◯ をクリア」を押してください')
    st.caption('4. まちがえたら「1手もどす」を使ってください')
    st.text_area('メモ', key='memo_text', height=140)

if st.session_state.bingo_card is None:
    st.info('左のサイドバーでシートサイズ・レベル・シード文字列を入力して「新しいビンゴを生成」を押してください。')
    st.stop()

rows, cols, center_pos, grid_size = get_board_spec(st.session_state.board_mode)
header_left, header_right = st.columns([1.2, 0.8])
with header_left:
    st.subheader(f"{st.session_state.board_mode} / レベル {st.session_state.current_level}")
with header_right:
    cleared = count_cleared(st.session_state.bingo_card)
    st.write(f"進捗: **{cleared} / {len(st.session_state.bingo_card)}**")

current_seed_label = st.session_state.last_seed_text if st.session_state.last_seed_text != '' else '（空欄）'
st.markdown(f"<div class='seed-note'>現在のシード文字列: <b>{html.escape(current_seed_label)}</b></div>", unsafe_allow_html=True)

render_legend()
st.write('')

for row in rows:
    row_columns = st.columns(grid_size, gap='small')
    for idx, col in enumerate(cols):
        pos = f'{col}-{row}'
        with row_columns[idx]:
            render_cell(pos, st.session_state.bingo_card[pos], is_small_board=(grid_size == 3))
