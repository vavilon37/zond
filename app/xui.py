"""3X-UI panel client.

Drop-in replacement for the old MarzbanClient. The bot used to talk to Marzban
(`POST /api/user` etc.); we now talk to 3X-UI (MHSanaei/3x-ui) instead.

3X-UI's REST API exposes inbound-level CRUD only — there's no addClient
endpoint in this version. To add/update/remove a single client we GET the
full inbound, mutate its `settings.clients` array, and POST the whole inbound
back via `/panel/api/inbounds/update/{id}`. Auth is Bearer token from
`x-ui setting -getApiToken` on the server.
"""
import json
import logging
import time
import uuid
from typing import Optional

import httpx

log = logging.getLogger(__name__)


class XuiClient:
    """Speaks to a single inbound in a 3X-UI panel.

    Compatible with the call-shape the rest of the bot expects from the old
    MarzbanClient: ``get_user``, ``create_user``, ``set_expire`` and
    ``normalize_sub_url``. ``expire`` values are unix seconds (the panel
    stores ms internally — we convert at the boundary).
    """

    def __init__(
        self,
        url: str,
        base_path: str,
        api_token: str,
        inbound_id: int,
        sub_base_url: str,
        sub_path: str,
        inbound_tag: str = "",  # kept for signature compat, unused
    ):
        self.base = url.rstrip("/") + "/" + base_path.strip("/")
        self.token = api_token
        self.inbound_id = inbound_id
        self.sub_base_url = sub_base_url.rstrip("/")
        self.sub_path = "/" + sub_path.strip("/")
        transport = httpx.AsyncHTTPTransport(retries=3, verify=True)
        self._client = httpx.AsyncClient(transport=transport, timeout=20)

    async def close(self) -> None:
        await self._client.aclose()

    def _hdr(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def _build_sub_url(self, sub_id: str) -> str:
        return f"{self.sub_base_url}{self.sub_path}/{sub_id}"

    @staticmethod
    def _settings_dict(inbound: dict) -> dict:
        s = inbound.get("settings")
        if isinstance(s, str):
            return json.loads(s)
        return s or {}

    @staticmethod
    def _stream_dict(inbound: dict, key: str) -> dict:
        s = inbound.get(key)
        if isinstance(s, str):
            return json.loads(s)
        return s or {}

    async def _get_inbound(self) -> dict:
        url = f"{self.base}/panel/api/inbounds/get/{self.inbound_id}"
        r = await self._client.get(url, headers=self._hdr())
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            raise RuntimeError(data.get("msg") or "3X-UI get failed")
        return data["obj"]

    async def _update_inbound(self, inbound: dict) -> dict:
        # 3X-UI expects settings/streamSettings/sniffing as JSON strings
        payload = dict(inbound)
        for key in ("settings", "streamSettings", "sniffing", "allocate"):
            v = payload.get(key)
            if isinstance(v, dict):
                payload[key] = json.dumps(v, ensure_ascii=False)
        url = f"{self.base}/panel/api/inbounds/update/{self.inbound_id}"
        r = await self._client.post(
            url,
            headers={**self._hdr(), "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            raise RuntimeError(data.get("msg") or "3X-UI update failed")
        return data["obj"]

    def _build_user_response(self, client: dict, traffic_used_bytes: int = 0) -> dict:
        expire_ms = client.get("expiryTime") or 0
        sub_id = client.get("subId") or client.get("email") or ""
        return {
            "username": client.get("email"),
            "expire": int(expire_ms // 1000) if expire_ms else 0,
            "subscription_url": self._build_sub_url(sub_id),
            "used_traffic": traffic_used_bytes,
            "uuid": client.get("id"),
            "status": "active" if client.get("enable", True) else "disabled",
        }

    async def get_user(self, email: str) -> Optional[dict]:
        try:
            inbound = await self._get_inbound()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        settings = self._settings_dict(inbound)
        used_by_email: dict[str, int] = {}
        for cs in inbound.get("clientStats") or []:
            cs_email = cs.get("email")
            if cs_email:
                used_by_email[cs_email] = int(cs.get("up", 0)) + int(cs.get("down", 0))
        for c in settings.get("clients", []):
            if c.get("email") == email:
                return self._build_user_response(c, used_by_email.get(email, 0))
        return None

    async def create_user(self, username: str, expire_ts: int) -> dict:
        """Add a new client to the inbound. ``username`` becomes the client's email.

        If the email already exists (e.g. concurrent /start), behaves as set_expire.
        """
        inbound = await self._get_inbound()
        settings = self._settings_dict(inbound)
        clients = settings.setdefault("clients", [])

        # idempotent: if exists, just set expire instead of creating
        for c in clients:
            if c.get("email") == username:
                c["expiryTime"] = expire_ts * 1000 if expire_ts else 0
                c["enable"] = True
                settings["clients"] = clients
                inbound["settings"] = settings
                await self._update_inbound(inbound)
                return self._build_user_response(c)

        new_client = {
            "id": str(uuid.uuid4()),
            "email": username,
            "enable": True,
            "expiryTime": expire_ts * 1000 if expire_ts else 0,
            "limitIp": 0,
            "totalGB": 0,
            "subId": username,
            "tgId": 0,
            "reset": 0,
            "flow": "",
            "comment": "",
            "created_at": int(time.time() * 1000),
            "updated_at": int(time.time() * 1000),
        }
        clients.append(new_client)
        settings["clients"] = clients
        inbound["settings"] = settings
        await self._update_inbound(inbound)
        log.info("xui: created client %s expire=%s", username, expire_ts)
        return self._build_user_response(new_client)

    async def set_expire(self, username: str, new_expire_ts: int) -> dict:
        inbound = await self._get_inbound()
        settings = self._settings_dict(inbound)
        clients = settings.setdefault("clients", [])
        for c in clients:
            if c.get("email") == username:
                c["expiryTime"] = new_expire_ts * 1000 if new_expire_ts else 0
                c["enable"] = True
                inbound["settings"] = settings
                await self._update_inbound(inbound)
                log.info("xui: set_expire %s -> %s", username, new_expire_ts)
                return self._build_user_response(c)
        # mirror Marzban: if missing, create
        return await self.create_user(username, new_expire_ts)

    def normalize_sub_url(self, sub_url: str) -> str:
        if not sub_url:
            return ""
        if sub_url.startswith("http"):
            return sub_url
        return f"{self.sub_base_url}{sub_url}"
