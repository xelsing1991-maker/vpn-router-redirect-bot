from __future__ import annotations

from app_config import MAIN_BOT_USERNAME


WELCOME_TEXT = """
<b>Подключение WireGuard VPN на роутере</b>

Этот бот помогает подключить VPN на роутере для проводного интернета.

Что здесь есть:
• инструкция для Keenetic
• список роутеров с поддержкой WireGuard-клиента
• переход в основной VPN-бот
• полезные каналы и ссылки

Для получения доступа и конфигурации переходите в @{main_bot}.
""".strip()

KEENETIC_TEXT = """
<b>Keenetic + WireGuard</b>

По официальной документации Keenetic, поддержка WireGuard есть у актуальных моделей начиная с KeeneticOS 3.3. Роутер может работать как VPN-сервер и как VPN-клиент.

Как подключить клиент:
1. Откройте веб-интерфейс Keenetic.
2. Установите компонент <b>WireGuard VPN</b>.
3. Перейдите в <b>Другие подключения → WireGuard</b>.
4. Импортируйте <code>.conf</code> файл.
5. Включите подключение.

Для клиентского режима белый IP от провайдера обычно не нужен.
Конфиг и доступ к VPN можно получить в @{main_bot}.
""".strip()

WIRED_TEXT = """
<b>WireGuard для проводного интернета</b>

Базовая схема:
1. Кабель провайдера подключается в WAN роутера.
2. На роутере включается WireGuard-клиент.
3. Загружается конфиг <code>.conf</code> от VPN.
4. Весь трафик дома или выбранные устройства идут через VPN.

Подходит для:
• Smart TV
• приставок
• ПК и ноутбуков
• всей домашней сети

VPN для роутера и готовый конфиг: @{main_bot}
""".strip()

ROUTERS_TEXT = """
<b>Роутеры и платформы с WireGuard-клиентом</b>

<b>Keenetic</b>
Актуальные модели с KeeneticOS 3.3+ и компонентом WireGuard VPN.

<b>MikroTik</b>
Роутеры на RouterOS v7 с интерфейсом WireGuard.

<b>OpenWrt</b>
Совместимые роутеры с установленным OpenWrt и пакетами WireGuard.

<b>GL.iNet</b>
Модели GL.iNet с официальной поддержкой WireGuard Client.

<b>ASUS</b>
Часть моделей с VPN Fusion и новой прошивкой. Например:
• GT6
• GT-AXE16000
• GT-AX11000 Pro
• GT-AX6000
• RT-AX88U Pro
• RT-AX86U Pro
• RT-AX68U
• RT-AX82U
• RT-AX58U
• RT-AX59U
• TUF-AX5400

<b>UniFi Gateway</b>
Шлюзы UniFi с функцией WireGuard VPN Client.

<b>TP-Link</b>
Только часть моделей и ревизий. Например:
• Archer AX57
• Archer AX55
• Archer AX53
• Archer AX23
• Archer AX72 / AX73 / AX75
• Archer AX80 / AX90
• Archer AXE75 / AXE95 / AXE300
• Archer BE220 / BE230 / BE260
• Archer BE3600 / BE5000 / BE600 / BE805 / BE900 / BE9300 / BE9500 / BE9700

Если у вас конкретная модель, её лучше проверять отдельно по версии прошивки.
""".strip()

SOURCES_TEXT = """
<b>Источники, проверено на 21.04.2026</b>

<a href="https://help.keenetic.com/hc/ru/articles/360010592379-WireGuard-VPN">Keenetic</a>
<a href="https://help.mikrotik.com/docs/spaces/ROS/pages/69664792/WireGuard">MikroTik</a>
<a href="https://openwrt.org/docs/guide-user/services/vpn/wireguard/client?s%5B%5D=vpn">OpenWrt</a>
<a href="https://docs.gl-inet.com/router/en/4/interface_guide/wireguard_client/">GL.iNet</a>
<a href="https://www.asus.com/us/support/faq/1048282/">ASUS</a>
<a href="https://routerkb.asuscomm.com/?page_id=9&lang=en">ASUS supported models</a>
<a href="https://help.ui.com/hc/en-us/articles/16357883221015-UniFi-Gateway-WireGuard-VPN-Client">UniFi Gateway</a>
<a href="https://www.tp-link.com/us/support/faq/3135/">TP-Link</a>
""".strip()


def build_main_text() -> str:
    return WELCOME_TEXT.format(main_bot=MAIN_BOT_USERNAME)


def build_info_text(key: str) -> str | None:
    info_map = {
        "keenetic": KEENETIC_TEXT.format(main_bot=MAIN_BOT_USERNAME),
        "routers": ROUTERS_TEXT,
        "wired": WIRED_TEXT.format(main_bot=MAIN_BOT_USERNAME),
        "sources": SOURCES_TEXT,
    }
    return info_map.get(key)
