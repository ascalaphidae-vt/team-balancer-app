import streamlit as st

def apply_theme():
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
    
        [data-testid="stTextArea"] textarea,
        [data-testid="stTextInput"] input {
    
    
            text-transform: none;
            autocapitalize: none;
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
            min-height: 2.8rem;
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
    
        @media (hover: hover) and (pointer: fine) {
        .stButton > button:enabled:hover,
        [data-testid="stFormSubmitButton"] > button:enabled:hover {
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
    
        @media (hover: hover) and (pointer: fine) {
        [data-testid="stCheckbox"] label:hover,
        [data-testid="stRadio"] label:hover {
            color: var(--soft-pink);
        }
        }

        .stButton > button,
        [data-testid="stFormSubmitButton"] > button,
        [data-testid="stCheckbox"] label,
        [data-testid="stRadio"] label {
            touch-action: manipulation;
        }

        @media (hover: none), (pointer: coarse) {
            .stButton > button:enabled:hover,
            [data-testid="stFormSubmitButton"] > button:enabled:hover {
                color: var(--text-main);
                border-color: rgba(110, 231, 242, 0.50);
                background: linear-gradient(135deg, rgba(18, 25, 32, 0.98), rgba(24, 17, 29, 0.98));
                transform: none;
            }

            .stButton > button[kind="primary"]:enabled:hover {
                color: #050609;
                background: linear-gradient(90deg, var(--soft-pink), var(--neon-cyan) 58%, var(--soft-lime));
            }

            [data-testid="stCheckbox"] label,
            [data-testid="stRadio"] label {
                min-height: 44px;
            }
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

        .team-members {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: var(--dark-panel);
            overflow: hidden;
        }

        .team-members.team-a { border-top: 4px solid #b2ed8a; }
        .team-members.team-b { border-top: 4px solid #ff9dca; }

        .team-player {
            padding: 12px 16px;
        }

        .team-player + .team-player {
            border-top: 1px solid rgba(185, 180, 196, 0.16);
        }

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
            color: var(--neon-cyan);
            font-size: 1.15rem;
            font-weight: 700;
            white-space: nowrap;
        }

        .team-player-rate small {
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 400;
        }

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
        .team-streak.winning { color: #ffe09a; }
        .team-streak.losing { color: #ff9dca; }
    
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
    
    
