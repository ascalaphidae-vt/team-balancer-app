import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        :root {
            --dark-bg: #07090c;
            --dark-panel: #101217;
            --dark-panel-2: #191c22;
            --neon-cyan: #69e6f2;
            --soft-pink: #d891ae;
            --soft-lime: #c7ee85;
            --text-main: #f5f3f7;
            --text-muted: #b1afba;
            --line: #34373f;
            --control-accent: var(--neon-cyan);
            --control-tint: #102127;
        }

        html, body, [class*="css"] {
            font-family: "Zen Maru Gothic", "Hiragino Maru Gothic ProN", "Yu Gothic", "Meiryo", sans-serif;
        }
        .stApp { color: var(--text-main); background: var(--dark-bg); }
        [data-testid="stHeader"] { background: rgba(7, 9, 12, 0.96); }
        [data-testid="stMainBlockContainer"] { max-width: 1540px; padding-top: 4.5rem; }
        h1, h2, h3 { color: var(--text-main); letter-spacing: 0.025em; }
        h2, h3 { border-left: 3px solid var(--soft-pink); padding-left: 0.7rem; }
        a { color: var(--soft-lime) !important; text-decoration-color: rgba(199, 238, 133, 0.5) !important; }
        hr { border-color: var(--line) !important; }
        [data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"] small { color: var(--text-muted); }

        [data-testid="stTextArea"] textarea,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input {
            color: var(--text-main);
            background: var(--dark-panel);
            border: 1px solid var(--line);
            border-radius: 8px;
        }
        [data-testid="stTextArea"] textarea:focus,
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus {
            border-color: var(--soft-lime);
            box-shadow: 0 0 0 1px rgba(199, 238, 133, 0.35);
        }
        [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stTextInput"] input::placeholder { color: #777580; }
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            color: var(--text-main);
            background: var(--dark-panel);
            border-color: var(--line);
        }
        [data-testid="stForm"] {
            padding: 1.1rem;
            border: 1px solid var(--line);
            border-radius: 12px;
            background: var(--dark-panel);
        }

        .stButton > button,
        [data-testid="stFormSubmitButton"] > button,
        [data-testid="stDownloadButton"] > button {
            min-height: 2.8rem;
            color: var(--text-main);
            font-weight: 700;
            border: 1px solid #3b4c51;
            border-radius: 8px;
            background: var(--dark-panel-2);
            box-shadow: none;
            touch-action: manipulation;
        }
        .stButton > button[kind="primary"],
        [data-testid="stFormSubmitButton"] > button[kind="primary"] {
            color: var(--neon-cyan);
            border-color: var(--neon-cyan);
            background: #102127;
        }
        .stButton > button:focus-visible,
        [data-testid="stFormSubmitButton"] > button:focus-visible,
        [data-testid="stDownloadButton"] > button:focus-visible {
            outline: 2px solid var(--neon-cyan);
            outline-offset: 3px;
        }
        .stButton > button:disabled,
        [data-testid="stFormSubmitButton"] > button:disabled,
        [data-testid="stDownloadButton"] > button:disabled {
            color: #797b83;
            border-color: #30333a;
            background: #111319;
            box-shadow: none;
        }

        [data-testid="stRadio"] [data-baseweb="radio"] {
            min-height: 44px;
            padding: 6px 10px;
            margin: 3px 6px 3px 0;
            border: 1px solid transparent;
            border-radius: 8px;
            color: var(--text-main);
            touch-action: manipulation;
        }
        [data-testid="stRadio"] [data-baseweb="radio"]:has(input:checked) {
            border-color: var(--control-accent);
            background: var(--control-tint);
        }
        [data-testid="stRadio"] [data-baseweb="radio"]:has(input:checked) > div:first-child {
            background-color: var(--control-accent);
        }
        [data-testid="stRadio"] [data-baseweb="radio"]:has(input:disabled) { opacity: 0.5; }
        [data-testid="stRadio"] input { accent-color: var(--control-accent); }
        [data-testid="stTabs"] button[aria-selected="true"] { color: var(--neon-cyan); }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] { background-color: var(--neon-cyan); }

        [data-testid="stAlert"] {
            color: var(--text-main);
            border: 1px solid var(--line);
            border-left: 3px solid var(--soft-lime);
            border-radius: 8px;
            background: var(--dark-panel);
        }
        [data-testid="stDataFrame"] {
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: var(--dark-panel);
        }

        .st-key-team_a_panel, .team-a { --team-accent: var(--neon-cyan); }
        .st-key-team_b_panel, .team-b { --team-accent: var(--soft-pink); }
        .team-heading {
            color: var(--team-accent);
            border-left-color: var(--team-accent);
            margin-bottom: 1rem;
            font-size: 1.45rem;
            font-weight: 700;
        }
        .st-key-team_a_panel [data-testid="stDataFrame"],
        .st-key-team_b_panel [data-testid="stDataFrame"] { border-color: var(--team-accent); }
        .team-members {
            border: 1px solid var(--line);
            border-top: 3px solid var(--team-accent);
            border-radius: 10px;
            background: var(--dark-panel);
            overflow: hidden;
        }
        .team-player { padding: 12px 16px; }
        .team-player + .team-player { border-top: 1px solid #292c33; }
        .team-player-heading {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 12px;
        }
        .team-player-name {
            min-width: 0;
            color: var(--text-main);
            font-size: 1.3rem;
            font-weight: 700;
            overflow-wrap: anywhere;
        }
        .team-player-rate {
            color: var(--team-accent);
            font-size: 1.15rem;
            font-weight: 700;
            white-space: nowrap;
        }
        .team-player-rate small { color: var(--text-muted); font-size: 0.8rem; font-weight: 400; }
        .team-player-stats {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px 14px;
            margin-top: 5px;
            color: var(--text-muted);
            font-size: 0.9rem;
        }
        .team-streak { color: var(--text-main); }
        .team-streak.winning { color: var(--soft-lime); }
        .st-key-winner_selection [data-baseweb="radio"]:nth-of-type(1) {
            --control-accent: var(--neon-cyan);
            --control-tint: #102127;
        }
        .st-key-winner_selection [data-baseweb="radio"]:nth-of-type(2) {
            --control-accent: var(--soft-pink);
            --control-tint: #251820;
        }

        [data-testid="stNumberInput"] button { color: var(--neon-cyan); background: var(--dark-panel-2); }
        code {
            color: var(--soft-lime) !important;
            background: #141a13 !important;
            border: 1px solid #3c4933;
            border-radius: 5px;
        }
        ::selection { color: var(--dark-bg); background: var(--soft-lime); }

        @media (hover: hover) and (pointer: fine) {
            .stButton > button:enabled:hover,
            [data-testid="stFormSubmitButton"] > button:enabled:hover,
            [data-testid="stDownloadButton"] > button:enabled:hover {
                color: var(--neon-cyan);
                border-color: var(--neon-cyan);
                background: #16282e;
            }
        }
        @media (hover: none), (pointer: coarse) {
            .stButton > button:enabled:hover,
            [data-testid="stFormSubmitButton"] > button:enabled:hover,
            [data-testid="stDownloadButton"] > button:enabled:hover {
                color: var(--text-main);
                border-color: #3b4c51;
                background: var(--dark-panel-2);
            }
            .stButton > button[kind="primary"]:enabled:hover,
            [data-testid="stFormSubmitButton"] > button[kind="primary"]:enabled:hover {
                color: var(--neon-cyan);
                border-color: var(--neon-cyan);
                background: #102127;
            }
        }
        @media (max-width: 700px) {
            [data-testid="stMainBlockContainer"] { padding-top: 3.5rem; }
            [data-testid="stForm"] { padding: 0.75rem; }
            .team-player-heading { flex-wrap: wrap; gap: 3px 12px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
