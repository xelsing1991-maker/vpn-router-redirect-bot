from __future__ import annotations

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from app_config import MAIN_BOT_URL
from app_storage import Storage


def format_admin_help() -> str:
    return (
        "<b>Админка</b>\n\n"
        "Что можно делать из меню:\n"
        "• смотреть общую сводку\n"
        "• смотреть онлайн-пользователей\n"
        "• открывать список ботов и каналов\n"
        "• добавлять новые боты\n"
        "• добавлять и удалять каналы\n"
        "• смотреть статистику по конкретному боту\n\n"
        "Быстрые команды:\n"
        "• /admin — открыть админку\n"
        "• /stats — статистика текущего бота\n"
        "• /cancel — отменить текущий ввод"
    )


def format_primary_admin_bot(storage: Storage) -> str:
    primary = storage.get_primary_admin_token()
    if not primary:
        return "<b>Главный админский бот</b>\n\nНе найден."
    return (
        "<b>Главный админский бот</b>\n\n"
        f"Первый токен в списке заканчивается на <code>{primary[-6:]}</code>.\n"
        "Именно в этом боте доступны админ-меню и управление."
    )


def build_main_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Перейти в VPN-бот", url=MAIN_BOT_URL))
    markup.add(InlineKeyboardButton("Keenetic", callback_data="info:keenetic"))
    markup.add(InlineKeyboardButton("Роутеры с WireGuard", callback_data="info:routers"))
    markup.add(InlineKeyboardButton("Проводной интернет", callback_data="info:wired"))
    markup.add(InlineKeyboardButton("Каналы", callback_data="info:channels"))
    markup.add(InlineKeyboardButton("Источники", callback_data="info:sources"))
    return markup


def build_back_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Перейти в VPN-бот", url=MAIN_BOT_URL))
    markup.add(InlineKeyboardButton("Назад в меню", callback_data="nav:home"))
    return markup


def build_channels_markup(storage: Storage) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    for channel in storage.load_channels():
        markup.add(InlineKeyboardButton(channel["title"], url=channel["url"]))
    markup.add(InlineKeyboardButton("Назад в меню", callback_data="nav:home"))
    return markup


def build_admin_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Сводка", callback_data="admin:overview"),
        InlineKeyboardButton("Онлайн", callback_data="admin:online"),
    )
    markup.add(
        InlineKeyboardButton("Мои боты", callback_data="admin:bots"),
        InlineKeyboardButton("Каналы", callback_data="admin:channels"),
    )
    markup.add(
        InlineKeyboardButton("Добавить бота", callback_data="admin:add_bot"),
        InlineKeyboardButton("Добавить канал", callback_data="admin:add_channel"),
    )
    markup.add(
        InlineKeyboardButton("Удалить канал", callback_data="admin:remove_channel"),
        InlineKeyboardButton("Статистика бота", callback_data="admin:stats_bot"),
    )
    markup.add(
        InlineKeyboardButton("Главный бот", callback_data="admin:primary_bot"),
        InlineKeyboardButton("Помощь", callback_data="admin:help"),
    )
    markup.add(
        InlineKeyboardButton("Отменить ввод", callback_data="admin:cancel"),
        InlineKeyboardButton("Обновить", callback_data="admin:overview"),
    )
    return markup
