from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from typing import Any

import telebot

from app_config import ADMIN_IDS, SERVICE_NAME
from app_storage import Storage
from app_texts import build_info_text, build_main_text
from app_ui import (
    build_admin_markup,
    build_back_markup,
    build_channels_markup,
    build_main_markup,
    format_admin_help,
    format_primary_admin_bot,
)


def validate_token_format(token: str) -> bool:
    left, sep, right = token.strip().partition(":")
    return bool(sep and left.isdigit() and right)


class BotManager:
    """Owns runtime state, starts bot threads and handles admin workflows."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self._admin_state_lock = threading.Lock()
        self._running_lock = threading.Lock()
        self._admin_states: dict[int, str] = {}
        self._running_tokens: set[str] = set()

    def is_admin(self, user_id: int | None) -> bool:
        return user_id in ADMIN_IDS

    def is_admin_bot(self, token: str) -> bool:
        return token == self.storage.get_primary_admin_token()

    def set_admin_state(self, user_id: int, state: str | None) -> None:
        with self._admin_state_lock:
            if state is None:
                self._admin_states.pop(user_id, None)
            else:
                self._admin_states[user_id] = state

    def get_admin_state(self, user_id: int) -> str | None:
        with self._admin_state_lock:
            return self._admin_states.get(user_id)

    def _mark_bot_as_running(self, token: str) -> bool:
        with self._running_lock:
            if token in self._running_tokens:
                return False
            self._running_tokens.add(token)
            return True

    def _unmark_bot_as_running(self, token: str) -> None:
        with self._running_lock:
            self._running_tokens.discard(token)

    def start_bot_thread(self, token: str) -> bool:
        if not self._mark_bot_as_running(token):
            return False
        thread = threading.Thread(
            target=self.run_bot,
            args=(token,),
            daemon=True,
            name=f"bot-{token[-6:]}",
        )
        thread.start()
        return True

    def start_all(self) -> None:
        for token in self.storage.load_tokens():
            self.start_bot_thread(token)

    def restart_service_after_delay(self, delay_seconds: float = 2.0) -> None:
        def worker() -> None:
            time.sleep(delay_seconds)
            if shutil.which("systemctl") is None:
                logging.warning("systemctl not found; skipping service restart")
                return
            try:
                subprocess.run(["systemctl", "restart", SERVICE_NAME], check=True)
            except Exception:
                logging.exception("Failed to restart service %s", SERVICE_NAME)

        threading.Thread(target=worker, daemon=True, name="service-restarter").start()

    def add_bot_token(self, token: str) -> tuple[bool, str]:
        clean_token = token.strip()
        if not validate_token_format(clean_token):
            return False, "Неверный формат токена."
        if clean_token in self.storage.load_tokens():
            return False, "Этот токен уже добавлен."
        try:
            bot_info = telebot.TeleBot(clean_token).get_me()
        except Exception:
            logging.exception("Failed to validate bot token")
            return False, "Не удалось проверить токен."
        self.storage.add_token(clean_token)
        username = bot_info.username or f"bot_{clean_token[-6:]}"
        return True, f"@{username}"

    def parse_channel_input(self, raw_value: str) -> tuple[bool, str, str]:
        raw = raw_value.strip()
        if not raw:
            return False, "", "Пустое значение."
        parts = [part.strip() for part in raw.split("|", maxsplit=1)]
        username = parts[0].lstrip("@")
        title = parts[1] if len(parts) > 1 and parts[1] else f"@{username}"
        if not username:
            return False, "", "Укажите username канала."
        return True, username, title

    def send_html(self, bot: telebot.TeleBot, chat_id: int, text: str, markup=None) -> None:
        bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)

    def send_main_message(self, bot: telebot.TeleBot, chat_id: int) -> None:
        self.send_html(bot, chat_id, build_main_text(), build_main_markup())

    def send_channels_message(self, bot: telebot.TeleBot, chat_id: int) -> None:
        if self.storage.load_channels():
            self.send_html(
                bot,
                chat_id,
                "<b>Наши каналы</b>\n\nВыберите канал из списка ниже.",
                build_channels_markup(self.storage),
            )
        else:
            self.send_html(bot, chat_id, "<b>Каналы пока не добавлены.</b>", build_back_markup())

    def send_admin_panel(self, bot: telebot.TeleBot, chat_id: int) -> None:
        self.send_html(bot, chat_id, self.storage.format_admin_overview(), build_admin_markup())

    def send_admin_prompt(self, bot: telebot.TeleBot, chat_id: int, text: str) -> None:
        self.send_html(bot, chat_id, text, build_admin_markup())

    def process_admin_text(self, bot: telebot.TeleBot, message: Any, state: str) -> bool:
        if not message.from_user:
            return False

        text = (message.text or "").strip()

        if state == "add_bot":
            ok, result = self.add_bot_token(text)
            self.set_admin_state(message.from_user.id, None)
            if ok:
                started_now = self.start_bot_thread(text.strip())
                if started_now:
                    result_text = f"{result} добавлен и запущен сразу в текущем процессе."
                else:
                    result_text = f"{result} добавлен. Бот уже запущен или будет поднят после рестарта."
                self.send_admin_prompt(
                    bot,
                    message.chat.id,
                    f"{result_text}\n\nЕсли на сервере есть systemd, сервис также будет перезапущен автоматически.",
                )
                self.restart_service_after_delay()
            else:
                self.send_admin_prompt(bot, message.chat.id, result)
            return True

        if state == "add_channel":
            ok, username, payload = self.parse_channel_input(text)
            self.set_admin_state(message.from_user.id, None)
            if not ok:
                self.send_admin_prompt(bot, message.chat.id, payload)
                return True
            channel_ok, result = self.storage.add_channel(username, payload)
            self.send_admin_prompt(bot, message.chat.id, result)
            return True

        if state == "remove_channel":
            self.set_admin_state(message.from_user.id, None)
            result_ok, result = self.storage.remove_channel(text.lstrip("@"))
            self.send_admin_prompt(bot, message.chat.id, result)
            return True

        if state == "stats_bot":
            self.set_admin_state(message.from_user.id, None)
            self.send_admin_prompt(bot, message.chat.id, self.storage.format_stats_for_bot(text.lstrip("@")))
            return True

        return False

    def run_bot(self, token: str) -> None:
        try:
            bot = telebot.TeleBot(token, parse_mode="HTML")
            bot_info = bot.get_me()
            bot_username = bot_info.username or f"bot_{token[-6:]}"
            admin_bot = self.is_admin_bot(token)

            @bot.message_handler(commands=["start", "help"])
            def handle_start(message: Any) -> None:
                from_user = message.from_user
                self.storage.record_event(
                    bot_username,
                    from_user.id if from_user else None,
                    from_user.username if from_user else None,
                    "start",
                    start=True,
                )
                self.send_main_message(bot, message.chat.id)

            @bot.message_handler(commands=["admin"])
            def handle_admin(message: Any) -> None:
                from_user = message.from_user
                if not admin_bot:
                    bot.reply_to(message, "Админка доступна только в главном боте.")
                    return
                if not self.is_admin(from_user.id if from_user else None):
                    bot.reply_to(message, "Нет доступа.")
                    return
                self.storage.record_event(bot_username, from_user.id, from_user.username, "admin_open")
                self.send_admin_panel(bot, message.chat.id)

            @bot.message_handler(commands=["cancel"])
            def handle_cancel(message: Any) -> None:
                from_user = message.from_user
                if not admin_bot:
                    bot.reply_to(message, "Админка доступна только в главном боте.")
                    return
                if not self.is_admin(from_user.id if from_user else None):
                    bot.reply_to(message, "Нет доступа.")
                    return
                self.set_admin_state(from_user.id, None)
                self.storage.record_event(bot_username, from_user.id, from_user.username, "admin_cancel")
                self.send_admin_prompt(bot, message.chat.id, "Текущий сценарий ввода отменён.")

            @bot.message_handler(commands=["stats"])
            def handle_stats(message: Any) -> None:
                from_user = message.from_user
                if not admin_bot:
                    bot.reply_to(message, "Статистика доступна только в главном боте.")
                    return
                if not self.is_admin(from_user.id if from_user else None):
                    bot.reply_to(message, "Нет доступа.")
                    return
                self.send_html(bot, message.chat.id, self.storage.format_stats_for_bot(bot_username), build_admin_markup())

            @bot.message_handler(commands=["add"])
            def handle_add(message: Any) -> None:
                from_user = message.from_user
                if not admin_bot:
                    bot.reply_to(message, "Добавление ботов доступно только в главном боте.")
                    return
                if not self.is_admin(from_user.id if from_user else None):
                    bot.reply_to(message, "Нет доступа.")
                    return
                parts = (message.text or "").split(maxsplit=1)
                if len(parts) < 2:
                    bot.reply_to(message, "Использование: /add <token>")
                    return

                clean_token = parts[1].strip()
                ok, result = self.add_bot_token(clean_token)
                if ok:
                    started_now = self.start_bot_thread(clean_token)
                    if started_now:
                        message_text = f"{result} добавлен и запущен сразу в текущем процессе."
                    else:
                        message_text = f"{result} добавлен. Бот уже запущен или будет поднят после рестарта."
                    self.send_html(bot, message.chat.id, message_text)
                    self.restart_service_after_delay()
                else:
                    bot.reply_to(message, result)

            @bot.message_handler(commands=["addchannel"])
            def handle_add_channel(message: Any) -> None:
                from_user = message.from_user
                if not admin_bot:
                    bot.reply_to(message, "Управление каналами доступно только в главном боте.")
                    return
                if not self.is_admin(from_user.id if from_user else None):
                    bot.reply_to(message, "Нет доступа.")
                    return
                parts = (message.text or "").split(maxsplit=1)
                if len(parts) < 2:
                    bot.reply_to(message, "Использование: /addchannel @username | Название")
                    return
                ok, username, payload = self.parse_channel_input(parts[1])
                if not ok:
                    bot.reply_to(message, payload)
                    return
                _, result = self.storage.add_channel(username, payload)
                bot.reply_to(message, result)

            @bot.message_handler(commands=["channels"])
            def handle_channels(message: Any) -> None:
                from_user = message.from_user
                self.storage.record_event(
                    bot_username,
                    from_user.id if from_user else None,
                    from_user.username if from_user else None,
                    "command_channels",
                )
                self.send_channels_message(bot, message.chat.id)

            @bot.message_handler(commands=["keenetic", "routers", "wired", "sources"])
            def handle_info_commands(message: Any) -> None:
                from_user = message.from_user
                command = (message.text or "").split()[0].lstrip("/").split("@")[0]
                text = build_info_text(command)
                if text is None:
                    self.send_main_message(bot, message.chat.id)
                    return
                self.storage.record_event(
                    bot_username,
                    from_user.id if from_user else None,
                    from_user.username if from_user else None,
                    f"command_{command}",
                )
                self.send_html(bot, message.chat.id, text, build_back_markup())

            @bot.callback_query_handler(func=lambda call: True)
            def handle_callbacks(call: Any) -> None:
                if call.data == "nav:home":
                    self.storage.record_event(bot_username, call.from_user.id, call.from_user.username, "nav_home")
                    bot.answer_callback_query(call.id)
                    self.send_main_message(bot, call.message.chat.id)
                    return

                if call.data.startswith("info:"):
                    key = call.data.split(":", maxsplit=1)[1]
                    if key == "channels":
                        self.storage.record_event(bot_username, call.from_user.id, call.from_user.username, "callback_channels")
                        bot.answer_callback_query(call.id, "Список каналов")
                        self.send_channels_message(bot, call.message.chat.id)
                        return
                    text = build_info_text(key)
                    if text is None:
                        bot.answer_callback_query(call.id)
                        return
                    self.storage.record_event(bot_username, call.from_user.id, call.from_user.username, f"callback_{key}")
                    bot.answer_callback_query(call.id)
                    self.send_html(bot, call.message.chat.id, text, build_back_markup())
                    return

                if not self.is_admin(call.from_user.id):
                    bot.answer_callback_query(call.id, "Нет доступа")
                    return
                if not admin_bot:
                    bot.answer_callback_query(call.id, "Админка только в главном боте")
                    return

                if call.data == "admin:overview":
                    bot.answer_callback_query(call.id, "Обновляю сводку")
                    self.send_html(bot, call.message.chat.id, self.storage.format_admin_overview(), build_admin_markup())
                    return
                if call.data == "admin:help":
                    bot.answer_callback_query(call.id, "Показываю помощь")
                    self.send_admin_prompt(bot, call.message.chat.id, format_admin_help())
                    return
                if call.data == "admin:primary_bot":
                    bot.answer_callback_query(call.id, "Показываю главный бот")
                    self.send_admin_prompt(bot, call.message.chat.id, format_primary_admin_bot(self.storage))
                    return
                if call.data == "admin:cancel":
                    self.set_admin_state(call.from_user.id, None)
                    bot.answer_callback_query(call.id, "Ввод отменён")
                    self.send_admin_prompt(bot, call.message.chat.id, "Текущий сценарий ввода отменён.")
                    return
                if call.data == "admin:online":
                    bot.answer_callback_query(call.id, "Показываю онлайн")
                    self.send_html(bot, call.message.chat.id, self.storage.format_online_users(), build_admin_markup())
                    return
                if call.data == "admin:bots":
                    bot.answer_callback_query(call.id, "Показываю боты")
                    self.send_html(bot, call.message.chat.id, self.storage.format_bots_list(), build_admin_markup())
                    return
                if call.data == "admin:channels":
                    bot.answer_callback_query(call.id, "Показываю каналы")
                    self.send_html(bot, call.message.chat.id, self.storage.format_channels_list(), build_admin_markup())
                    return
                if call.data == "admin:add_bot":
                    self.set_admin_state(call.from_user.id, "add_bot")
                    bot.answer_callback_query(call.id, "Отправьте токен нового бота")
                    self.send_admin_prompt(bot, call.message.chat.id, "Отправьте новым сообщением токен бота в формате:\n<code>123:ABC</code>")
                    return
                if call.data == "admin:add_channel":
                    self.set_admin_state(call.from_user.id, "add_channel")
                    bot.answer_callback_query(call.id, "Отправьте канал")
                    self.send_admin_prompt(bot, call.message.chat.id, "Отправьте новым сообщением:\n<code>@username | Название канала</code>")
                    return
                if call.data == "admin:remove_channel":
                    self.set_admin_state(call.from_user.id, "remove_channel")
                    bot.answer_callback_query(call.id, "Отправьте username канала")
                    self.send_admin_prompt(bot, call.message.chat.id, "Отправьте новым сообщением username канала для удаления:\n<code>@channel_name</code>")
                    return
                if call.data == "admin:stats_bot":
                    self.set_admin_state(call.from_user.id, "stats_bot")
                    bot.answer_callback_query(call.id, "Введите username бота")
                    self.send_admin_prompt(bot, call.message.chat.id, "Отправьте username бота без токена:\n<code>mybot</code> или <code>@mybot</code>")
                    return
                bot.answer_callback_query(call.id)

            @bot.message_handler(func=lambda message: True)
            def fallback_handler(message: Any) -> None:
                from_user = message.from_user
                state = self.get_admin_state(from_user.id if from_user else 0)
                if state and self.is_admin(from_user.id if from_user else None):
                    if self.process_admin_text(bot, message, state):
                        self.storage.record_event(bot_username, from_user.id, from_user.username, f"admin_state_{state}")
                        return
                self.storage.record_event(
                    bot_username,
                    from_user.id if from_user else None,
                    from_user.username if from_user else None,
                    "fallback",
                )
                self.send_main_message(bot, message.chat.id)

            logging.info("Started bot @%s", bot_username)

            while True:
                try:
                    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
                except Exception as exc:
                    logging.exception("Bot polling failed for token ending with %s: %s", token[-6:], exc)
                    time.sleep(5)
        finally:
            self._unmark_bot_as_running(token)
