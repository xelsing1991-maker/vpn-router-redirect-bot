from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

SERVICE_NAME = "botvpnredirect"

TOKENS_FILE = BASE_DIR / "bot_tokens.json"
STATS_FILE = BASE_DIR / "button_stats.json"
CHANNELS_FILE = BASE_DIR / "channels.json"
ENV_FILE = BASE_DIR / ".env"

ONLINE_WINDOW_SECONDS = 300
MAX_ONLINE_USERS = 20
MAX_TOP_USERS = 10

def _load_dotenv(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        logging.exception("Could not read %s", path)
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_admin_ids(value: str) -> set[int]:
    admin_ids: set[int] = set()
    for item in _split_csv(value):
        try:
            admin_ids.add(int(item))
        except ValueError:
            logging.warning("Ignoring invalid admin id: %s", item)
    return admin_ids


_load_dotenv()

MAIN_BOT_USERNAME = os.getenv("MAIN_BOT_USERNAME", "your_vpn_bot")
MAIN_BOT_URL = os.getenv("MAIN_BOT_URL", f"https://t.me/{MAIN_BOT_USERNAME}")

# Telegram user IDs with full admin access. Set as comma-separated IDs.
ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

# Optional comma-separated fallback tokens. Prefer bot_tokens.json on servers.
DEFAULT_BOT_TOKENS = _split_csv(os.getenv("BOT_TOKENS", ""))


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(threadName)s %(message)s",
    )


def configure_runtime_encoding() -> None:
    # Force UTF-8 output so Windows consoles do not corrupt Cyrillic logs.
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                logging.debug("Could not reconfigure %s to utf-8", stream_name)
