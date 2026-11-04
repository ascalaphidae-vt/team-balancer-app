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
            "settings": deepcopy(DEFAULT_SETTINGS), "bulk_text": "", "private_sessions": []}


def touch(state):
    # A management undo must not roll back unrelated changes made afterwards.
    state.pop("profile_management_undo", None)
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


def current_private(state):
    return next((p for p in reversed(state.get("private_sessions", [])) if p["ended_at"] is None), None)


def _remember_members(state, rows):
    private = current_private(state)
    if private is None:
        return
    for row in rows:
        name, rate = row["name"], row["rate"]
        if name not in private["members"]:
            private["members"][name] = profile(name, rate)
        else:
            private["members"][name]["rate"] = rate


def _start_private(state, rows, started_at=None):
    sessions = state.setdefault("private_sessions", [])
    private = {"id": uuid.uuid4().hex, "number": len(sessions) + 1,
               "started_at": started_at or now(), "ended_at": None, "members": {}}
    # New private counters start at zero, including when upgrading old cumulative rests.
    for p in state["profiles"].values():
        p["rests"] = 0
    sessions.append(private)
    _remember_members(state, rows)
    return private


def end_private(state):
    require_idle(state)
    private = current_private(state)
    if private is None:
        raise ValueError("進行中のプラベがありません。最初のチーム分けで開始します。")
    # Members are stored independently, so clearing live counters cannot erase this table.
    for name, member in private["members"].items():
        if name in state["profiles"]:
            member["rate"] = state["profiles"][name]["rate"]
    private["ended_at"] = now()
    for p in state["profiles"].values():
        p["rests"] = 0
    touch(state)


def result_reopen_reason(state, match):
    private = current_private(state)
    if private is None or match.get("private_id") != private["id"]:
        return "終了済み、または今回より前のプラベの結果は取り消せません。必要な累計値は手動編集してください。"
    if match["number"] <= state.get("result_undo_blocked_through", 0):
        return "プレイヤー記録を整理・編集したため、それ以前の結果は取り消せません。必要な数値は手動編集してください。"
    return None


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
            state.get("profile_links", {}).pop(name, None)
        else:
            state["profiles"][name]["rate"] = rate
        state["roster"][row["slot"]].update(name=name, rate=str(rate))
    _remember_members(state, rows)
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
    if name not in state["profiles"]:
        raise ValueError("そのプレイヤーは記録に登録されていません。一覧を選び直してください。")
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
    private = current_private(state)
    if private is None:
        private = _start_private(state, rows)
    match = {"id": uuid.uuid4().hex, "number": len(state["history"]) + 1,
             "private_id": private["id"],
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
    private = current_private(state)
    if private is None or match.get("private_id") != private["id"]:
        raise ValueError("この試合のプラベが進行中ではありません。")
    members_before = {name: deepcopy(private["members"][name]) for name in names}
    members_updated = deepcopy(members_before)
    updated = deepcopy(before)
    for change in changes:
        p = updated[change["name"]]
        p["rate"] = change["after"]
        p["matches"] += 1
        p["wins" if change["won"] else "losses"] += 1
        p["streak"] = change["streak"]
        member = members_updated[change["name"]]
        member["rate"] = change["after"]
        member["matches"] += 1
        member["wins" if change["won"] else "losses"] += 1
        member["streak"] = next_streak(member["streak"], change["won"])
    for name in match["resting"]:
        updated[name]["rests"] += 1  # Rest neither breaks nor advances a streak.
        members_updated[name]["rests"] += 1
    state["profiles"].update(updated)
    private["members"].update(members_updated)
    match.update(status="recorded", winner=winner, changes=changes,
                 recorded_at=now(), profiles_before=before, private_members_before=members_before)
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
    reason = result_reopen_reason(state, match)
    if reason:
        raise ValueError(reason)
    # Restore only the people in that match, keeping profiles registered later.
    state["profiles"].update(deepcopy(match["profiles_before"]))
    current_private(state)["members"].update(deepcopy(match["private_members_before"]))
    sync_rates(state, match["profiles_before"])
    match.setdefault("corrections", []).append({"winner": match["winner"], "at": now()})
    match.update(status="pending", winner=None, selected_winner=None, changes=[])
    match.pop("recorded_at", None)
    match.pop("profiles_before", None)
    match.pop("private_members_before", None)
    touch(state)


def reset_roster(state):
    require_idle(state)
    state["roster"] = empty_roster()
    state["bulk_text"] = ""
    touch(state)


MANAGEMENT_KEYS = ("profiles", "roster", "bulk_text", "profile_links", "result_undo_blocked_through", "private_sessions")


def _management_change(state, operation, label):
    """Commit atomically, retaining one recoverable management operation."""
    require_idle(state)
    candidate = deepcopy(state)
    saved = {k: deepcopy(state.get(k, [] if k == "private_sessions" else {} if k == "profile_links" else 0)) for k in MANAGEMENT_KEYS}
    operation(candidate)
    candidate["result_undo_blocked_through"] = max(
        candidate.get("result_undo_blocked_through", 0),
        max((m["number"] for m in candidate["history"] if m["status"] == "recorded"), default=0))
    candidate["bulk_text"] = ""  # Do not leave obsolete names in the bulk-entry draft.
    touch(candidate)
    candidate["profile_management_undo"] = {"label": label, "data": saved}
    state.clear()
    state.update(candidate)


def undo_profile_management(state):
    require_idle(state)
    undo = state.get("profile_management_undo")
    if not undo:
        raise ValueError("元に戻せる整理・編集がありません。")
    restored = deepcopy(undo["data"])
    state.update(restored)
    touch(state)


def _require_profile(state, name):
    if name not in state["profiles"]:
        raise ValueError("選んだプレイヤーは登録されていません。")


def _redirect_profile(state, old_name, new_name):
    links = state.setdefault("profile_links", {})
    for alias, target in list(links.items()):
        if target == old_name:
            links[alias] = new_name
    links[old_name] = new_name
    if new_name is not None:
        links.pop(new_name, None)


def _update_roster_identity(state, old_name, new_name):
    indexes = [i for i, r in enumerate(state["roster"]) if clean_name(r["name"]) in (old_name, new_name)]
    if not indexes:
        return
    active = any(state["roster"][i]["active"] for i in indexes)
    # Prefer the existing destination slot. Inactive named slots are never overwritten.
    keep = next((i for i in indexes if clean_name(state["roster"][i]["name"]) == new_name), indexes[0])
    for i in indexes:
        state["roster"][i] = empty_roster()[0]
    if new_name is not None:
        state["roster"][keep] = {"name": new_name, "rate": str(state["profiles"][new_name]["rate"]), "active": active}


def _rename_private_member(state, old_name, new_name):
    private = current_private(state)
    if private is None or old_name not in private["members"]:
        return
    old = private["members"].pop(old_name)
    if new_name in private["members"]:
        dest = private["members"][new_name]
        for key in ("matches", "wins", "losses", "rests"):
            dest[key] += old[key]
    else:
        dest = dict(old, name=new_name)
        private["members"][new_name] = dest
    dest["rate"] = state["profiles"][new_name]["rate"]


def edit_profile(state, name, values):
    def edit(s):
        _require_profile(s, name)
        new_name = clean_name(values["name"])
        if not new_name:
            raise ValueError("名前を入力してください。")
        if new_name != name and new_name in s["profiles"]:
            raise ValueError("その名前は登録済みです。同じ人物なら「統合」を使ってください。")
        updated = {"name": new_name, "initial_rate": parse_rate(values["initial_rate"]),
                   "rate": parse_rate(values["rate"])}
        for key in ("wins", "losses", "rests", "streak"):
            value = values[key]
            if type(value) is not int:
                raise ValueError("勝敗・休憩・連勝連敗は整数で入力してください。")
            updated[key] = value
        updated["matches"] = updated["wins"] + updated["losses"]
        if any(not 0 <= updated[k] <= 1_000_000_000 for k in ("wins", "losses", "rests", "matches")):
            raise ValueError("勝敗・休憩・試合数は0〜10億の範囲で入力してください。")
        if not -updated["losses"] <= updated["streak"] <= updated["wins"]:
            raise ValueError("連勝数は勝利数以下、連敗数は敗北数以下にしてください。")
        _validate_profile(updated, new_name)
        s["profiles"].pop(name)
        s["profiles"][new_name] = updated
        if new_name != name:
            _redirect_profile(s, name, new_name)
            _rename_private_member(s, name, new_name)
        private = current_private(s)
        if private and new_name in private["members"]:
            private["members"][new_name].update(rate=updated["rate"], rests=updated["rests"])
        _update_roster_identity(s, name, new_name)
    _management_change(state, edit, "プレイヤー記録の手動編集")


def merge_profiles(state, source, target, initial_from="target", rate_from="target"):
    def merge(s):
        _require_profile(s, source)
        _require_profile(s, target)
        if source == target:
            raise ValueError("異なる2人を選んでください。")
        if initial_from not in ("source", "target") or rate_from not in ("source", "target"):
            raise ValueError("残すレートを選び直してください。")
        a, b = s["profiles"][source], s["profiles"][target]
        combined = deepcopy(b)
        for key in ("matches", "wins", "losses", "rests"):
            combined[key] = a[key] + b[key]
        combined["initial_rate"] = (a if initial_from == "source" else b)["initial_rate"]
        combined["rate"] = (a if rate_from == "source" else b)["rate"]
        _validate_profile(combined, target)
        s["profiles"][target] = combined
        del s["profiles"][source]
        _redirect_profile(s, source, target)
        _rename_private_member(s, source, target)
        private = current_private(s)
        if private and target in private["members"]:
            private["members"][target]["rate"] = combined["rate"]
        _update_roster_identity(s, source, target)
    _management_change(state, merge, "プレイヤー記録の統合")


def delete_profile(state, name):
    def delete(s):
        _require_profile(s, name)
        del s["profiles"][name]
        _redirect_profile(s, name, None)
        _update_roster_identity(s, name, None)
    _management_change(state, delete, "プレイヤー記録の削除")


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


def _validate_privates(state, legacy):
    if legacy:
        if any(m.get("private_id") is not None for m in state["history"]):
            raise ValueError("プラベ一覧が保存されていません。")
        state["private_sessions"] = []
        pending = pending_match(state)
        if pending:
            # Only an unfinished legacy match can be assigned a reliable boundary.
            rows = pending["team_a"] + pending["team_b"] + [
                {"name": name, "rate": state["profiles"][name]["rate"]} for name in pending["resting"]]
            private = _start_private(state, rows, started_at=pending["created_at"])
            pending["private_id"] = private["id"]
    sessions = state["private_sessions"]
    if not isinstance(sessions, list):
        raise ValueError("プラベ一覧の保存データが不正です。")
    by_id = {}
    for index, private in enumerate(sessions):
        if not isinstance(private, dict) or not isinstance(private.get("id"), str) or not private["id"] or private["id"] in by_id:
            raise ValueError("プラベの識別情報が不正です。")
        _integer(private.get("number"), 1, 1_000_000_000)
        if private["number"] != index + 1:
            raise ValueError("プラベの順序が不正です。")
        if not isinstance(private.get("started_at"), str) or not private["started_at"]:
            raise ValueError("プラベの開始日時が不正です。")
        if private.get("ended_at") is None:
            if index != len(sessions) - 1:
                raise ValueError("進行中のプラベが重複しています。")
        elif not isinstance(private["ended_at"], str) or not private["ended_at"]:
            raise ValueError("プラベの終了日時が不正です。")
        members = private.get("members")
        if not isinstance(members, dict):
            raise ValueError("今回のメンバーの保存データが不正です。")
        for name, member in members.items():
            if not clean_name(name) or clean_name(name) != name:
                raise ValueError("今回のメンバー名が不正です。")
            _validate_profile(member, name)
        by_id[private["id"]] = private
    for match in state["history"]:
        private_id = match.get("private_id")
        if private_id is None:
            if match["status"] == "pending":
                raise ValueError("未入力の試合にプラベが設定されていません。")
            continue  # Completed matches from before this feature stay in lifetime history.
        if not isinstance(private_id, str) or private_id not in by_id:
            raise ValueError("試合のプラベが見つかりません。")
        private = by_id[private_id]
        names = {p["name"] for p in match["team_a"] + match["team_b"]} | set(match["resting"])
        if match["status"] == "pending":
            if private["ended_at"] is not None or not names <= set(private["members"]):
                raise ValueError("未入力試合のプラベまたはメンバーが不正です。")
        if match["status"] == "recorded":
            before = match.get("private_members_before")
            if not isinstance(before, dict) or set(before) != names:
                raise ValueError("今回の戦績を取り消すためのデータが不足しています。")
            for name, member in before.items():
                _validate_profile(member, name)


def import_state(raw):
    """Unknown/malformed backups must never partially replace a working session."""
    if len(raw.encode("utf-8")) > MAX_BACKUP_BYTES:
        raise ValueError("バックアップは4MB以下にしてください。")
    try:
        s = json.loads(raw)
        if not isinstance(s, dict) or s.get("version") != VERSION:
            raise ValueError("このバージョンのバックアップではありません。")
        legacy = "private_sessions" not in s
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
        links = s.get("profile_links", {})
        if not isinstance(links, dict):
            raise ValueError("統合・削除した名前の保存データが不正です。")
        for alias, target in links.items():
            if not clean_name(alias) or clean_name(alias) != alias or alias in s["profiles"]:
                raise ValueError("統合・削除した名前の保存データが不正です。")
            if target is not None and (not isinstance(target, str) or target not in s["profiles"]):
                raise ValueError("統合先の保存データが不正です。")
        _integer(s.get("result_undo_blocked_through", 0), high=1_000_000_000)
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
                if p["name"] not in s["profiles"] and (m["status"] == "pending" or p["name"] not in links):
                    raise ValueError("試合の参加者が登録されていません。")
                names.append(p["name"])
            rests = m["resting"]
            if not isinstance(rests, list) or any(n not in s["profiles"] and (m["status"] == "pending" or n not in links) for n in rests) or len(set(names + rests)) != len(names + rests):
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
        # Old result snapshots must never resurrect a removed/renamed profile.
        for m in s["history"]:
            if m["status"] == "recorded" and any(n not in s["profiles"] for n in m["profiles_before"]):
                if m["number"] > s.get("result_undo_blocked_through", 0):
                    raise ValueError("整理済みプレイヤーの取り消し範囲が不正です。")
        _validate_privates(s, legacy)
        undo = s.get("profile_management_undo")
        if undo is not None:
            if legacy and isinstance(undo, dict) and isinstance(undo.get("data"), dict):
                undo["data"].setdefault("private_sessions", [])
            if not isinstance(undo, dict) or not isinstance(undo.get("label"), str) or set(undo.get("data", {})) != set(MANAGEMENT_KEYS):
                raise ValueError("整理を元に戻すための保存データが不正です。")
            previous = deepcopy(s)
            previous.pop("profile_management_undo")
            previous.update(undo["data"])
            import_state(export_state(previous))
        return s
    except (KeyError, TypeError, AttributeError, OverflowError, RecursionError, json.JSONDecodeError) as e:
        raise ValueError("保存データを読み込めません。正しいJSONバックアップを選んでください。") from e
