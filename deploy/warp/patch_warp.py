#!/usr/bin/env python3
"""
Добавить Cloudflare Warp wireguard outbound и routing для TikTok/ByteDance
в /var/lib/marzban/xray_config.json.

Запуск: sudo python3 patch_warp.py
"""
import json
import re
import sys
from pathlib import Path

XRAY_CONFIG = Path("/var/lib/marzban/xray_config.json")
WGCF_PROFILE = Path("/opt/warp/wgcf-profile.conf")

# Домены TikTok/ByteDance, чей трафик пускаем через Warp
TIKTOK_DOMAINS = [
    "domain:tiktok.com",
    "domain:tiktokv.com",
    "domain:tiktokv.us",
    "domain:tiktokcdn.com",
    "domain:tiktokcdn-eu.com",
    "domain:tiktokcdn-us.com",
    "domain:byteoversea.com",
    "domain:bytedance.com",
    "domain:bytedance.net",
    "domain:musical.ly",
    "domain:ibyteimg.com",
    "domain:byteimg.com",
    "domain:ipstatp.com",
    "domain:sgsnssdk.com",
    "domain:tt-events.com",
    "domain:isnssdk.com",
    "domain:ttwstatic.com",
]


def parse_wgcf(path: Path) -> dict:
    text = path.read_text()
    g = lambda pat: (m.group(1).strip() if (m := re.search(pat, text, re.M)) else None)
    addresses_raw = g(r"^Address\s*=\s*(.+)$")
    return {
        "addresses": [a.strip() for a in addresses_raw.split(",")] if addresses_raw else None,
        "private_key": g(r"^PrivateKey\s*=\s*(.+)$"),
        "public_key": g(r"^PublicKey\s*=\s*(.+)$"),
        "endpoint": g(r"^Endpoint\s*=\s*(.+)$"),
    }


def main():
    if not WGCF_PROFILE.exists():
        sys.exit(f"Файл {WGCF_PROFILE} не найден. Сначала запусти setup.sh")
    if not XRAY_CONFIG.exists():
        sys.exit(f"Файл {XRAY_CONFIG} не найден")

    wg = parse_wgcf(WGCF_PROFILE)
    missing = [k for k, v in wg.items() if not v]
    if missing:
        sys.exit(f"В wgcf-profile.conf не нашёл: {missing}. Файл: {wg}")

    print(f"Warp endpoint: {wg['endpoint']}")
    print(f"Warp addresses: {wg['addresses']}")

    config = json.loads(XRAY_CONFIG.read_text())

    # Бэкап
    backup = XRAY_CONFIG.with_suffix(".json.before_warp.bak")
    backup.write_text(json.dumps(config, indent=2))
    print(f"Бэкап: {backup}")

    # Outbound
    warp_outbound = {
        "tag": "warp",
        "protocol": "wireguard",
        "settings": {
            "secretKey": wg["private_key"],
            "address": wg["addresses"],
            "peers": [{
                "publicKey": wg["public_key"],
                "endpoint": wg["endpoint"],
                "allowedIPs": ["0.0.0.0/0", "::/0"],
            }],
            "mtu": 1280,
            "kernelMode": False,
        },
    }
    outbounds = config.setdefault("outbounds", [])
    outbounds[:] = [o for o in outbounds if o.get("tag") != "warp"]
    outbounds.append(warp_outbound)

    # Routing rule
    routing = config.setdefault("routing", {})
    rules = routing.setdefault("rules", [])
    rules[:] = [r for r in rules if r.get("outboundTag") != "warp"]
    rules.insert(0, {
        "type": "field",
        "outboundTag": "warp",
        "domain": TIKTOK_DOMAINS,
    })

    XRAY_CONFIG.write_text(json.dumps(config, indent=2))
    print(f"Обновлён {XRAY_CONFIG}")
    print("Теперь: sudo marzban restart")


if __name__ == "__main__":
    main()
