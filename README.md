# VPN Router Redirect Bot

Telegram-бот для редиректа пользователей в основной VPN-бот и выдачи справочной информации по WireGuard на роутерах. В комплекте есть админ-панель, управление несколькими ботами, каналы и простая статистика активности.

## Возможности

- запуск нескольких Telegram-ботов в одном процессе;
- публичное меню с инструкциями по Keenetic, WireGuard и роутерам;
- кнопка перехода в основной VPN-бот;
- админ-панель через `/admin`;
- добавление ботов и каналов из Telegram;
- статистика запусков, действий и онлайн-пользователей;
- установка как `systemd`-сервис на Ubuntu.

## Быстрая установка с GitHub

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/xelsing1991-maker/vpn_router_redirect.git
cd vpn_router_redirect
chmod +x install_ubuntu.sh
sudo ./install_ubuntu.sh
```

После установки настройте секреты на сервере:

```bash
sudo nano /opt/botvpnredirect/.env
sudo nano /opt/botvpnredirect/bot_tokens.json
sudo systemctl restart botvpnredirect
```

Пример `.env`:

```env
ADMIN_IDS=123456789
MAIN_BOT_USERNAME=your_vpn_bot
MAIN_BOT_URL=https://t.me/your_vpn_bot
```

Пример `/opt/botvpnredirect/bot_tokens.json`:

```json
[
  "123456789:replace_with_telegram_bot_token"
]
```

Первый токен в `bot_tokens.json` считается главным ботом. Только в нем доступны админ-команды управления ботами и каналами.

## Локальный запуск

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
cp bot_tokens.example.json bot_tokens.json
python multi_bot_redirect.py
```

На Windows используйте:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item bot_tokens.example.json bot_tokens.json
python multi_bot_redirect.py
```

## Админ-команды

- `/admin` - открыть админ-панель;
- `/stats` - статистика текущего бота;
- `/add <token>` - добавить нового бота;
- `/addchannel @username | Название` - добавить канал;
- `/cancel` - отменить текущий ввод.

## Файлы данных

Эти файлы создаются локально и не публикуются в git:

- `bot_tokens.json` - токены Telegram-ботов;
- `channels.json` - кнопки каналов;
- `button_stats.json` - статистика активности;
- `.env` - admin ID и настройки основного VPN-бота.

Для репозитория оставлены только безопасные примеры: `.env.example`, `bot_tokens.example.json`, `channels.example.json`, `button_stats.example.json`.

## Systemd

```bash
sudo systemctl status botvpnredirect
sudo journalctl -u botvpnredirect -f
sudo systemctl restart botvpnredirect
```

## Безопасность

Не коммитьте реальные токены, user ID администраторов и статистику пользователей. Если токен уже попадал в публичный репозиторий, перевыпустите его через BotFather.
