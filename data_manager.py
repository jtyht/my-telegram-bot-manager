import json
import os
import time

DATA_FILE = "data.json"

def _load():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _ensure_chat(data, chat_id):
    if chat_id not in data:
        data[chat_id] = {"settings": {}, "warns": {}, "flood": {}}
    if "settings" not in data[chat_id]:
        data[chat_id]["settings"] = {}
    if "warns" not in data[chat_id]:
        data[chat_id]["warns"] = {}
    if "flood" not in data[chat_id]:
        data[chat_id]["flood"] = {}

# ─── SETTINGS ───────────────────────────────────────────────────────────────

def get_settings(chat_id: str) -> dict:
    data = _load()
    _ensure_chat(data, chat_id)
    return data[chat_id]["settings"]

def update_setting(chat_id: str, key: str, value):
    data = _load()
    _ensure_chat(data, chat_id)
    data[chat_id]["settings"][key] = value
    _save(data)

# ─── WARNS ──────────────────────────────────────────────────────────────────

def add_warn(chat_id: str, user_id: str) -> int:
    data = _load()
    _ensure_chat(data, chat_id)
    warns = data[chat_id]["warns"]
    warns[user_id] = warns.get(user_id, 0) + 1
    _save(data)
    return warns[user_id]

def get_warns(chat_id: str, user_id: str) -> int:
    data = _load()
    _ensure_chat(data, chat_id)
    return data[chat_id]["warns"].get(user_id, 0)

def clear_warns(chat_id: str, user_id: str):
    data = _load()
    _ensure_chat(data, chat_id)
    data[chat_id]["warns"].pop(user_id, None)
    _save(data)

# ─── FLOOD ──────────────────────────────────────────────────────────────────

def increment_flood(chat_id: str, user_id: str) -> int:
    data = _load()
    _ensure_chat(data, chat_id)
    flood = data[chat_id]["flood"]
    now = time.time()
    if user_id not in flood or now - flood[user_id]["time"] > 10:
        flood[user_id] = {"count": 1, "time": now}
    else:
        flood[user_id]["count"] += 1
    _save(data)
    return flood[user_id]["count"]

def reset_flood(chat_id: str, user_id: str):
    data = _load()
    _ensure_chat(data, chat_id)
    data[chat_id]["flood"].pop(user_id, None)
    _save(data)
