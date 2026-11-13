"""Transient OBS display for the current match."""
from html import escape
import re
from threading import Lock
from time import monotonic
from urllib.parse import urlencode, urlsplit, urlunsplit

import streamlit as st


HEARTBEAT = 10
# Chrome can reduce timer frequency to once a minute in a background tab.
FEED_TIMEOUT = 150
LINK_IDLE_LIMIT = 60 * 60
PUBLIC_APP_URL = "https://team-balancer-app-97fuwx3goz5y3znabrw7ie.streamlit.app/"


def valid_key(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{48}", value) is not None


def browser_source_url(key, app_url=None):
    url = urlsplit(app_url or PUBLIC_APP_URL)
    # Community Cloud wraps the root in a branded shell even with embed enabled.
    path = "/~/+/" if url.hostname and url.hostname.endswith(".streamlit.app") else url.path
    query = urlencode({"embed": "true", "obs": key})
    return urlunsplit((url.scheme, url.netloc, path, query, ""))


def strongest_player(match):
    if match is None:
        return ""
    players = match["team_a"] + match["team_b"]
    return min(players, key=lambda player: (-player["rate"], player["name"]))["name"]


class OverlayFeeds:
    def __init__(self):
        self._feeds = {}
        self._lock = Lock()

    def start(self, key, owner, name):
        with self._lock:
            now = monotonic()
            self._feeds = {k: feed for k, feed in self._feeds.items() if now - feed[2] < LINK_IDLE_LIMIT}
            self._feeds[key] = (owner, name, now)

    def publish(self, key, owner, name):
        with self._lock:
            feed = self._feeds.get(key)
            if feed is None or feed[0] != owner:
                return False
            self._feeds[key] = (owner, name, monotonic())
            return True

    def stop(self, key, owner):
        with self._lock:
            feed = self._feeds.get(key)
            if feed is not None and feed[0] == owner:
                del self._feeds[key]

    def read(self, key):
        with self._lock:
            feed = self._feeds.get(key)
            if feed is not None and monotonic() - feed[2] < FEED_TIMEOUT:
                return feed[1]
            return ""


@st.cache_resource
def overlay_feeds():
    return OverlayFeeds()


OVERLAY_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@900&display=swap');
html, body, [data-testid="stApp"] {
    background: #00ff00 !important;
    overflow: hidden !important;
}
[data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }
.leader-overlay {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: grid;
    place-content: center;
    background: #00ff00;
    padding: 10px 18px 15px;
    text-align: center;
    font-family: "Zen Maru Gothic", "Hiragino Maru Gothic ProN", "Meiryo", sans-serif;
    font-weight: 900;
}
.leader-label, .leader-name {
    margin: 0;
    line-height: 1.18;
    paint-order: stroke fill;
}
.leader-label {
    color: #fff1a3;
    font-size: clamp(16px, 18vh, 30px);
    letter-spacing: .08em;
    -webkit-text-stroke: .24em #301347;
    text-shadow: 0 .15em #301347;
}
.leader-name {
    color: #fff8fe;
    font-size: clamp(20px, 36vh, 60px);
    letter-spacing: .015em;
    -webkit-text-stroke: .21em #301347;
    text-shadow: 0 .14em #db4fb2, 0 .22em #301347;
    overflow-wrap: anywhere;
}
.leader-name[data-size="medium"] { font-size: clamp(17px, 29vh, 48px); }
.leader-name[data-size="long"] { font-size: clamp(15px, 20vh, 33px); }
.leader-name[data-size="extra-long"] { font-size: clamp(12px, 14vh, 22px); }
.leader-crown {
    display: inline-block;
    margin-inline-end: .17em;
    font-size: .83em;
    -webkit-text-stroke: 0;
    text-shadow: none;
    filter: drop-shadow(0 2px 0 #301347) drop-shadow(0 3px 1px #301347);
}
</style>
"""


def overlay_markup(name):
    content = ""
    if name:
        size = "extra-long" if len(name) > 45 else "long" if len(name) > 22 else "medium" if len(name) > 11 else "short"
        content = (f'<div class="leader-label">現在の最強プレイヤー</div>'
                   f'<div class="leader-name" data-size="{size}">'
                   f'<span class="leader-crown" aria-hidden="true">👑</span><bdi>{escape(name)}</bdi></div>')
    return f'<div class="leader-overlay">{content}</div>'


def show_overlay(key):
    st.html(OVERLAY_CSS)
    if not valid_key(key):
        st.html(overlay_markup(""))
        return

    @st.fragment(run_every="1s")
    def display_leader():
        st.html(overlay_markup(overlay_feeds().read(key)))

    display_leader()
