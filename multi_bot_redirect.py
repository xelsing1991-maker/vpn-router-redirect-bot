from __future__ import annotations

import time

from app_config import configure_runtime_encoding, setup_logging
from app_runtime import BotManager
from app_storage import Storage


def main() -> None:
    # Runtime bootstrap is intentionally small so the real logic stays in modules.
    setup_logging()
    configure_runtime_encoding()

    storage = Storage()
    storage.migrate_files()

    manager = BotManager(storage)
    manager.start_all()

    # Keep the parent process alive while bot polling runs in daemon threads.
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
