from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from app_config import (
    CHANNELS_FILE,
    DEFAULT_BOT_TOKENS,
    MAX_ONLINE_USERS,
    MAX_TOP_USERS,
    ONLINE_WINDOW_SECONDS,
    STATS_FILE,
    TOKENS_FILE,
)


class Storage:
    """Thread-safe JSON storage for bot tokens, channels and statistics."""

    def __init__(self) -> None:
        self._tokens_lock = threading.Lock()
        self._channels_lock = threading.Lock()
        self._stats_lock = threading.Lock()

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logging.exception("Failed to read %s", path)
            return default

    def _save_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_tokens(self) -> list[str]:
        data = self._load_json(TOKENS_FILE, [])
        if isinstance(data, list):
            tokens = [str(item).strip() for item in data if str(item).strip()]
            if tokens:
                return tokens
        if DEFAULT_BOT_TOKENS:
            self.save_tokens(DEFAULT_BOT_TOKENS)
            return DEFAULT_BOT_TOKENS.copy()
        return []

    def save_tokens(self, tokens: list[str]) -> None:
        self._save_json(TOKENS_FILE, tokens)

    def get_primary_admin_token(self) -> str | None:
        tokens = self.load_tokens()
        return tokens[0] if tokens else None

    def add_token(self, token: str) -> bool:
        with self._tokens_lock:
            tokens = self.load_tokens()
            if token in tokens:
                return False
            tokens.append(token)
            self.save_tokens(tokens)
            return True

    def load_channels(self) -> list[dict[str, str]]:
        data = self._load_json(CHANNELS_FILE, [])
        channels: list[dict[str, str]] = []
        if not isinstance(data, list):
            return channels

        for item in data:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            username = str(item.get("username", "")).strip().lstrip("@")
            if not title:
                title = f"@{username}" if username else "Канал"
            if not url and username:
                url = f"https://t.me/{username}"
            if url:
                channels.append({"title": title, "url": url, "username": username})
        return channels

    def save_channels(self, channels: list[dict[str, str]]) -> None:
        self._save_json(CHANNELS_FILE, channels)

    def add_channel(self, username: str, title: str) -> tuple[bool, str]:
        with self._channels_lock:
            channels = self.load_channels()
            for item in channels:
                if item.get("username", "").lower() == username.lower():
                    return False, "Этот канал уже добавлен."
            channels.append(
                {
                    "title": title or f"@{username}",
                    "username": username,
                    "url": f"https://t.me/{username}",
                }
            )
            self.save_channels(channels)
        return True, f"Канал @{username} добавлен."

    def remove_channel(self, username: str) -> tuple[bool, str]:
        with self._channels_lock:
            channels = self.load_channels()
            new_channels = [item for item in channels if item.get("username", "").lower() != username.lower()]
            if len(new_channels) == len(channels):
                return False, "Канал не найден."
            self.save_channels(new_channels)
        return True, f"Канал @{username} удалён."

    def _normalize_user_stats(self, user_stats: Any) -> dict[str, Any]:
        if not isinstance(user_stats, dict):
            return {"username": "", "actions": 0, "last_seen": 0}
        return {
            "username": str(user_stats.get("username", "")).strip(),
            "actions": int(user_stats.get("actions", user_stats.get("clicks", 0)) or 0),
            "last_seen": int(user_stats.get("last_seen", 0) or 0),
        }

    def _normalize_bot_stats(self, bot_stats: Any) -> dict[str, Any]:
        if not isinstance(bot_stats, dict):
            return {"starts": 0, "actions": {}, "users": {}, "_variants_migrated": True}

        actions: dict[str, int] = {}
        raw_actions = bot_stats.get("actions", {})
        if isinstance(raw_actions, dict):
            for action_name, count in raw_actions.items():
                actions[str(action_name)] = int(count or 0)

        variants = bot_stats.get("variants", {})
        if isinstance(variants, dict) and not bot_stats.get("_variants_migrated"):
            for variant in variants.values():
                if not isinstance(variant, dict):
                    continue
                action_name = str(variant.get("text", "button"))
                actions[action_name] = actions.get(action_name, 0) + int(variant.get("clicks", 0) or 0)

        users: dict[str, dict[str, Any]] = {}
        raw_users = bot_stats.get("users", {})
        if isinstance(raw_users, dict):
            for user_id, user_stats in raw_users.items():
                users[str(user_id)] = self._normalize_user_stats(user_stats)

        return {
            "starts": int(bot_stats.get("starts", bot_stats.get("total_clicks", 0)) or 0),
            "actions": actions,
            "users": users,
            "_variants_migrated": True,
        }

    def load_stats(self) -> dict[str, Any]:
        raw = self._load_json(STATS_FILE, {"bots": {}})
        if not isinstance(raw, dict):
            raw = {"bots": {}}
        raw_bots = raw.get("bots", {})
        bots: dict[str, dict[str, Any]] = {}
        if isinstance(raw_bots, dict):
            for bot_name, bot_stats in raw_bots.items():
                bots[str(bot_name)] = self._normalize_bot_stats(bot_stats)
        return {"bots": bots}

    def save_stats(self, stats: dict[str, Any]) -> None:
        self._save_json(STATS_FILE, stats)

    def migrate_files(self) -> None:
        if not TOKENS_FILE.exists() or self.load_tokens():
            self.save_tokens(self.load_tokens())
        self.save_channels(self.load_channels())
        self.save_stats(self.load_stats())

    def get_bot_stats(self, stats: dict[str, Any], bot_username: str) -> dict[str, Any]:
        bots = stats.setdefault("bots", {})
        return bots.setdefault(
            bot_username,
            {
                "starts": 0,
                "actions": {},
                "users": {},
                "_variants_migrated": True,
            },
        )

    def record_event(
        self,
        bot_username: str,
        user_id: int | None,
        username: str | None,
        action: str,
        *,
        start: bool = False,
    ) -> None:
        now = int(time.time())
        with self._stats_lock:
            stats = self.load_stats()
            bot_stats = self.get_bot_stats(stats, bot_username)
            if start:
                bot_stats["starts"] = int(bot_stats.get("starts", 0)) + 1

            actions = bot_stats.setdefault("actions", {})
            actions[action] = int(actions.get(action, 0)) + 1

            if user_id is not None:
                users = bot_stats.setdefault("users", {})
                user_stats = users.setdefault(
                    str(user_id),
                    {"username": username or "", "actions": 0, "last_seen": 0},
                )
                user_stats["username"] = username or user_stats.get("username", "")
                user_stats["actions"] = int(user_stats.get("actions", 0)) + 1
                user_stats["last_seen"] = now

            self.save_stats(stats)

    def get_overall_metrics(self) -> dict[str, Any]:
        stats = self.load_stats()
        channels = self.load_channels()
        bots = stats.get("bots", {})
        cutoff = int(time.time()) - ONLINE_WINDOW_SECONDS

        total_starts = 0
        total_actions = 0
        unique_users: dict[str, dict[str, Any]] = {}

        for bot_name, bot_stats in bots.items():
            if not isinstance(bot_stats, dict):
                continue
            total_starts += int(bot_stats.get("starts", 0))
            total_actions += sum(int(v) for v in bot_stats.get("actions", {}).values())

            users = bot_stats.get("users", {})
            if not isinstance(users, dict):
                continue
            for user_id, user_stats in users.items():
                if not isinstance(user_stats, dict):
                    continue
                current_last_seen = int(user_stats.get("last_seen", 0))
                previous = unique_users.get(user_id)
                if previous is None or current_last_seen > int(previous.get("last_seen", 0)):
                    unique_users[user_id] = {
                        "username": user_stats.get("username", ""),
                        "actions": int(user_stats.get("actions", 0)),
                        "last_seen": current_last_seen,
                        "bot": bot_name,
                    }

        online_users = [
            (user_id, user_stats, str(user_stats.get("bot", "")))
            for user_id, user_stats in unique_users.items()
            if int(user_stats.get("last_seen", 0)) >= cutoff
        ]
        online_users.sort(key=lambda item: int(item[1].get("last_seen", 0)), reverse=True)

        return {
            "bot_count": len(self.load_tokens()),
            "channel_count": len(channels),
            "total_starts": total_starts,
            "total_actions": total_actions,
            "unique_users": len(unique_users),
            "online_users": online_users,
        }

    def format_admin_overview(self) -> str:
        metrics = self.get_overall_metrics()
        return (
            "<b>Админ-панель</b>\n\n"
            f"Ботов подключено: <b>{metrics['bot_count']}</b>\n"
            f"Каналов добавлено: <b>{metrics['channel_count']}</b>\n"
            f"Всего запусков /start: <b>{metrics['total_starts']}</b>\n"
            f"Всего действий в боте: <b>{metrics['total_actions']}</b>\n"
            f"Уникальных пользователей: <b>{metrics['unique_users']}</b>\n"
            f"Онлайн за последние {ONLINE_WINDOW_SECONDS // 60} мин: <b>{len(metrics['online_users'])}</b>"
        )

    def format_online_users(self) -> str:
        users = self.get_overall_metrics()["online_users"][:MAX_ONLINE_USERS]
        if not users:
            return (
                "<b>Онлайн-посетители</b>\n\n"
                f"За последние {ONLINE_WINDOW_SECONDS // 60} минут активных пользователей нет."
            )
        lines = [
            "<b>Онлайн-посетители</b>",
            "",
            f"Активность за последние {ONLINE_WINDOW_SECONDS // 60} минут:",
        ]
        now = int(time.time())
        for user_id, user_stats, bot_name in users:
            username = user_stats.get("username") or "без username"
            seconds_ago = now - int(user_stats.get("last_seen", 0))
            lines.append(f"• {user_id} (@{username}) — @{bot_name} — {seconds_ago} сек. назад")
        return "\n".join(lines)

    def format_bots_list(self) -> str:
        lines = ["<b>Подключённые боты</b>", ""]
        for index, token in enumerate(self.load_tokens(), start=1):
            lines.append(f"{index}. токен заканчивается на <code>{token[-6:]}</code>")
        lines.append("")
        lines.append("Чтобы добавить новый бот, нажмите кнопку ниже.")
        return "\n".join(lines)

    def format_channels_list(self) -> str:
        channels = self.load_channels()
        lines = ["<b>Каналы</b>", ""]
        if not channels:
            lines.append("Список пуст.")
        else:
            for index, channel in enumerate(channels, start=1):
                lines.append(f"{index}. {channel['title']} — {channel['url']}")
        return "\n".join(lines)

    def format_stats_for_bot(self, bot_username: str) -> str:
        bot_stats = self.load_stats().get("bots", {}).get(bot_username)
        if not bot_stats:
            return f"<b>Статистика @{bot_username}</b>\n\nДанных пока нет."

        lines = [
            f"<b>Статистика @{bot_username}</b>",
            "",
            f"Запусков /start: {bot_stats.get('starts', 0)}",
            "",
            "Действия:",
        ]

        actions = bot_stats.get("actions", {})
        if actions:
            for action_name, count in sorted(actions.items(), key=lambda item: item[1], reverse=True):
                lines.append(f"• {action_name}: {count}")
        else:
            lines.append("Нет данных")

        lines.append("")
        lines.append("Топ пользователей:")
        users = bot_stats.get("users", {})
        if users:
            sorted_users = sorted(
                users.items(),
                key=lambda item: int(item[1].get("actions", 0)),
                reverse=True,
            )[:MAX_TOP_USERS]
            for user_id, item in sorted_users:
                username = item.get("username") or "без username"
                lines.append(f"• {user_id} (@{username}) — {item.get('actions', 0)}")
        else:
            lines.append("Нет данных")

        return "\n".join(lines)
