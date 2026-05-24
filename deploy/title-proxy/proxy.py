"""Reverse-proxy для Marzban /sub/* — динамически подменяет profile-title с днями."""
import base64
import re
import time

from aiohttp import ClientSession, ClientTimeout, web

MARZBAN_URL = "http://127.0.0.1:8001"
TITLE_BASE = "Zond VPN"

SESSION_KEY = "mz_session"


def days_left_label(expire_ts: int) -> str:
    now = int(time.time())
    if expire_ts <= now:
        return "истёк"
    seconds_left = expire_ts - now
    days = seconds_left // 86400
    hours = (seconds_left % 86400) // 3600
    minutes = (seconds_left % 3600) // 60
    if days > 0:
        return f"{days}д {hours}ч"
    if hours > 0:
        return f"{hours}ч"
    if minutes > 0:
        return f"{minutes}мин"
    return "<1мин"


async def handle_sub(request: web.Request) -> web.Response:
    session: ClientSession = request.app[SESSION_KEY]
    rest = request.match_info["rest"]
    upstream_url = f"{MARZBAN_URL}/sub/{rest}"
    if request.query_string:
        upstream_url += f"?{request.query_string}"

    forward_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    async with session.get(upstream_url, headers=forward_headers, allow_redirects=False) as r:
        content = await r.read()
        response_headers = dict(r.headers)
        status = r.status

    userinfo = response_headers.get("subscription-userinfo", "")
    m = re.search(r"expire=(\d+)", userinfo)
    if m:
        label = days_left_label(int(m.group(1)))
        title_text = f"{TITLE_BASE} | {label}"
    else:
        title_text = TITLE_BASE

    title_b64 = base64.b64encode(title_text.encode("utf-8")).decode("ascii")
    response_headers["profile-title"] = f"base64:{title_b64}"

    for h in ("content-length", "transfer-encoding", "content-encoding", "connection"):
        response_headers.pop(h, None)

    return web.Response(body=content, status=status, headers=response_headers)


async def _on_startup(app: web.Application) -> None:
    app[SESSION_KEY] = ClientSession(timeout=ClientTimeout(total=15))


async def _on_cleanup(app: web.Application) -> None:
    await app[SESSION_KEY].close()


def main() -> None:
    app = web.Application()
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)
    app.router.add_route("GET", "/sub/{rest:.*}", handle_sub)
    web.run_app(app, host="127.0.0.1", port=8002, access_log=None)


if __name__ == "__main__":
    main()
