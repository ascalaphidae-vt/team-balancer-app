"""Streamlit に依存しない、保存データと試合処理。"""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
import itertools
import json
import random
import re
import unicodedata
import uuid

VERSION = 2
MAX_RATE = 999999
MAX_BACKUP_BYTES = 4_000_000
DEFAULT_SETTINGS = {"decrease": True, "percent": 3.0, "streak_bonus": True}


def now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def empty_roster():
    return [{"name": "", "rate": "2000", "active": False} for _ in range(10)]


def new_state():
    return {"version": VERSION, "revision": 0, "updated_at": now(),
            "roster": empty_roster(), "profiles": {}, "history": [],
            "settings": deepcopy(DEFAULT_SETTINGS), "bulk_text": ""}


def touch(state):
    state["revision"] += 1
    state["updated_at"] = now()


def clean_name(value):
    name = unicodedata.normalize("NFC", str(value)).strip()
    if len(name) > 80 or any(ord(c) < 32 for c in name):
        raise ValueError("名前は改行を含まない80文字以内で入力してください。")
    return name


def parse_rate(value):
    text = unicodedata.normalize("NFKC", str(value)).strip().replace(",", "")
    if not re.fullmatch(r"[0-9]{1,6}", text):
        raise ValueError("レートは0〜999999の整数で入力してください（全角数字も使えます）。")
    return int(text)


def profile(name, rate):
    return {"name": name, "initial_rate": rate, "rate": rate,
            "matches": 0, "wins": 0, "losses": 0, "rests": 0, "streak": 0}


def pending_match(state):
    return next((m for m in reversed(state["history"]) if m["status"] == "pending"), None)


def require_idle(state):
    if pending_match(state):
        raise ValueError("結果未入力の試合があります。結果を登録するか、この試合を中止してください。")


def validated_roster(state):
    result, seen = [], set()
    for i, row in enumerate(state["roster"]):
        name = clean_name(row["name"])
        if not name:
            if row["active"]:
                raise ValueError(f"枠{i + 1}は参加ONですが、名前が空欄です。")
            continue
        if name in seen:
            raise ValueError(f"「{name}」が重複しています。同名の人は区別できる名前にしてください。")
        seen.add(name)
        result.append({"slot": i, "name": name, "rate": parse_rate(row["rate"]),
                       "active": row["active"]})
    return result


def commit_roster(state):
    require_idle(state)
    rows = validated_roster(state)  # Validate everything before changing anything.
    for row in rows:
        name, rate = row["name"], row["rate"]
        if name not in state["profiles"]:
            state["profiles"][name] = profile(name, rate)
        else:
            state["profiles"][name]["rate"] = rate
        state["roster"][row["slot"]].update(name=name, rate=str(rate))
    touch(state)


def parse_bulk(text, limit=10):
    entries = [e.strip() for e in re.split(r"[,、;；\n]+", text) if e.strip()]
    if not entries:
        raise ValueError("名前：レート を入力してください。")
    if limit is not None and len(entries) > limit:
        raise ValueError("入力できるのは10人までです。入力内容は変更していません。")
    rows, seen = [], set()
    for entry in entries:
        parts = re.split(r"[:：\t]", entry, maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"「{entry}」を 名前：レート の形式にしてください。")
        name = clean_name(parts[0])
        if not name or name in seen:
            raise ValueError(f"名前が空欄または重複しています：{entry}")
        seen.add(name)
        rows.append({"name": name, "rate": str(parse_rate(parts[1])), "active": True})
    return rows


def apply_bulk(state, text):
    require_idle(state)
    rows = parse_bulk(text)
    state["roster"] = rows + empty_roster()[len(rows):]
    commit_roster(state)


def load_profile(state, name, use_initial=False):
    require_idle(state)
    if any(clean_name(p["name"]) == name for p in state["roster"]):
        raise ValueError("そのプレイヤーはすでに入力されています。")
    # An inactive named player is resting, not an empty slot.
    slot = next((p for p in state["roster"] if not clean_name(p["name"])), None)
    if slot is None:
        raise ValueError("空の枠がありません。名前が空欄の枠を用意してください。")
    p = state["profiles"][name]
    slot.update(name=name, rate=str(p["initial_rate"] if use_initial else p["rate"]), active=True)
    touch(state)


def assign_teams(players):
    """最小の合計レート差。同じ差の候補はランダムで選ぶ。"""
    n, best, candidates = len(players), float("inf"), []
    for indexes in itertools.combinations(range(n), n // 2):
        if n % 2 == 0 and 0 not in indexes:
            continue  # Mirrored teams are equivalent.
        a = [players[i] for i in indexes]
        b = [players[i] for i in range(n) if i not in indexes]
        diff = abs(sum(p["rate"] for p in a) - sum(p["rate"] for p in b))
        if diff < best:
            best, candidates = diff, [(a, b)]
        elif diff == best:
            candidates.append((a, b))
    if not candidates:
        raise ValueError("参加者を2人以上選んでください。")
    a, b = random.choice(candidates)
    return deepcopy(a), deepcopy(b), best


def create_match(state):
    require_idle(state)
    rows = validated_roster(state)
    playing = [p for p in rows if p["active"]]
    if not 2 <= len(playing) <= 8:
        raise ValueError("参加者は2〜8人にしてください。残りの人は参加をOFFにすると休憩になります。")
    a, b, diff = assign_teams(playing)
    commit_roster(state)
    match = {"id": uuid.uuid4().hex, "number": len(state["history"]) + 1,
             "created_at": now(), "status": "pending", "winner": None,
             "team_a": a, "team_b": b,
             "resting": [p["name"] for p in rows if not p["active"]],
             "settings": deepcopy(state["settings"]), "diff": diff, "changes": []}
    state["history"].append(match)
    touch(state)
    return match


def next_streak(previous, won):
    return max(previous, 0) + 1 if won else min(previous, 0) - 1


def calculate_change(rate, won, streak, settings):
    factor = min(Decimal("2"), Decimal("1") + Decimal("0.25") * (abs(streak) - 1))
    if not settings["streak_bonus"]:
        factor = Decimal("1")
    amount = int((Decimal(rate) * Decimal(str(settings["percent"])) / 100 * factor)
                 .quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if settings["percent"] > 0:
        amount = max(1, amount)
    if won:
        return min(MAX_RATE, rate + amount) - rate
    return -min(rate, amount) if settings["decrease"] else 0


def preview_result(state, match, winner):
    if winner not in ("A", "B"):
        raise ValueError("勝利チームを選んでください。")
    winning = {p["name"] for p in match["team_a" if winner == "A" else "team_b"]}
    changes = []
    for p in match["team_a"] + match["team_b"]:
        name, rate = p["name"], p["rate"]
        won = name in winning
        streak = next_streak(state["profiles"][name]["streak"], won)
        delta = calculate_change(rate, won, streak, match["settings"])
        changes.append({"name": name, "before": rate, "after": rate + delta,
                        "delta": delta, "won": won, "streak": streak})
    return changes


def sync_rates(state, names):
    for row in state["roster"]:
        name = clean_name(row["name"])
        if name in names:
            row["rate"] = str(state["profiles"][name]["rate"])


def record_result(state, match_id, winner):
    match = pending_match(state)
    if not match or match["id"] != match_id:
        raise ValueError("この試合は登録済み、または中止済みです。二重登録は行いません。")
    changes = preview_result(state, match, winner)
    names = {c["name"] for c in changes} | set(match["resting"])
    before = {name: deepcopy(state["profiles"][name]) for name in names}
    updated = deepcopy(before)
    for change in changes:
        p = updated[change["name"]]
        p["rate"] = change["after"]
        p["matches"] += 1
        p["wins" if change["won"] else "losses"] += 1
        p["streak"] = change["streak"]
    for name in match["resting"]:
        updated[name]["rests"] += 1  # Rest neither breaks nor advances a streak.
    state["profiles"].update(updated)
    match.update(status="recorded", winner=winner, changes=changes,
                 recorded_at=now(), profiles_before=before)
    sync_rates(state, names)
    touch(state)


def cancel_match(state, match_id):
    match = pending_match(state)
    if not match or match["id"] != match_id:
        raise ValueError("中止できる未入力の試合がありません。")
    match.update(status="void", cancelled_at=now())
    touch(state)


def reopen_last_result(state):
    require_idle(state)
    match = next((m for m in reversed(state["history"]) if m["status"] == "recorded"), None)
    if not match:
        raise ValueError("取り消せる結果がありません。")
    # Restore only the people in that match, keeping profiles registered later.
    state["profiles"].update(deepcopy(match["profiles_before"]))
    sync_rates(state, match["profiles_before"])
    match.setdefault("corrections", []).append({"winner": match["winner"], "at": now()})
    match.update(status="pending", winner=None, selected_winner=None, changes=[])
    match.pop("recorded_at", None)
    match.pop("profiles_before", None)
    touch(state)


def reset_roster(state):
    require_idle(state)
    state["roster"] = empty_roster()
    state["bulk_text"] = ""
    touch(state)


def export_state(state):
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _integer(value, low=0, high=MAX_RATE):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("保存データ内の数値が不正です。")


def _validate_profile(p, name):
    if not isinstance(p, dict) or p.get("name") != name:
        raise ValueError("プレイヤーの保存データが不正です。")
    for key in ("initial_rate", "rate"):
        _integer(p.get(key))
    for key in ("matches", "wins", "losses", "rests"):
        _integer(p.get(key), high=1_000_000_000)
    _integer(p.get("streak"), -p["losses"], p["wins"])
    if p["matches"] != p["wins"] + p["losses"]:
        raise ValueError("試合数と勝敗数が一致しません。")


def _validate_settings(s):
    if not isinstance(s, dict) or type(s.get("decrease")) is not bool or type(s.get("streak_bonus")) is not bool:
        raise ValueError("レート設定の保存データが不正です。")
    if type(s.get("percent")) not in (int, float) or not 0 <= s["percent"] <= 20:
        raise ValueError("レート変動率は0〜20%にしてください。")


def import_state(raw):
    """Unknown/malformed backups must never partially replace a working session."""
    if len(raw.encode("utf-8")) > MAX_BACKUP_BYTES:
        raise ValueError("バックアップは4MB以下にしてください。")
    try:
        s = json.loads(raw)
        if not isinstance(s, dict) or s.get("version") != VERSION:
            raise ValueError("このバージョンのバックアップではありません。")
        _integer(s["revision"], high=1_000_000_000)
        if not isinstance(s["updated_at"], str) or not isinstance(s["bulk_text"], str):
            raise ValueError("保存データの形式が不正です。")
        _validate_settings(s["settings"])
        if not isinstance(s["roster"], list) or len(s["roster"]) != 10:
            raise ValueError("プレイヤー枠の保存データが不正です。")
        for row in s["roster"]:
            if not isinstance(row["name"], str) or not isinstance(row["rate"], str) or type(row["active"]) is not bool:
                raise ValueError("入力欄の保存データが不正です。")
            clean_name(row["name"])  # Draft rates may still be incomplete.
        if not isinstance(s["profiles"], dict) or not isinstance(s["history"], list):
            raise ValueError("記録の保存データが不正です。")
        for name, p in s["profiles"].items():
            if not clean_name(name) or clean_name(name) != name:
                raise ValueError("保存された名前が不正です。")
            _validate_profile(p, name)
        ids, pending, recorded_after_pending = set(), False, False
        for index, m in enumerate(s["history"]):
            if not isinstance(m["id"], str) or m["id"] in ids or m["status"] not in ("pending", "recorded", "void"):
                raise ValueError("試合の保存データが不正です。")
            ids.add(m["id"])
            _integer(m["number"], 1, 1_000_000_000)
            if not isinstance(m["created_at"], str):
                raise ValueError("試合日時が不正です。")
            _validate_settings(m["settings"])
            if m.get("selected_winner") not in (None, "A", "B"):
                raise ValueError("選択中の勝利チームが不正です。")
            a, b = m["team_a"], m["team_b"]
            if not isinstance(a, list) or not isinstance(b, list) or not a or not b or not 2 <= len(a) + len(b) <= 8:
                raise ValueError("チームの保存データが不正です。")
            names = []
            for p in a + b:
                _integer(p["slot"], 0, 9)
                _integer(p["rate"])
                if p["name"] not in s["profiles"]:
                    raise ValueError("試合の参加者が登録されていません。")
                names.append(p["name"])
            rests = m["resting"]
            if not isinstance(rests, list) or any(n not in s["profiles"] for n in rests) or len(set(names + rests)) != len(names + rests):
                raise ValueError("参加者または休憩者が重複しています。")
            if m["diff"] != abs(sum(p["rate"] for p in a) - sum(p["rate"] for p in b)):
                raise ValueError("チームのレート差が不正です。")
            if m["status"] == "pending":
                if pending or m["winner"] is not None or m["changes"]:
                    raise ValueError("未入力試合の保存データが不正です。")
                pending = True
                if any(s["profiles"][p["name"]]["rate"] != p["rate"] for p in a + b):
                    raise ValueError("未入力試合と最新レートが一致しません。")
            elif m["status"] == "recorded":
                recorded_after_pending = pending
                if recorded_after_pending or m["winner"] not in ("A", "B") or not isinstance(m.get("recorded_at"), str):
                    raise ValueError("試合結果の保存データが不正です。")
                if set(m["profiles_before"]) != set(names + rests):
                    raise ValueError("取り消し用データが不足しています。")
                for name, p in m["profiles_before"].items():
                    _validate_profile(p, name)
                expected = preview_result({"profiles": m["profiles_before"]}, m, m["winner"])
                if m["changes"] != expected:
                    raise ValueError("レート変動の保存データが不正です。")
        return s
    except (KeyError, TypeError, AttributeError, OverflowError, RecursionError, json.JSONDecodeError) as e:
        raise ValueError("保存データを読み込めません。正しいJSONバックアップを選んでください。") from e
