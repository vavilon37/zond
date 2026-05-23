import time
from typing import Optional

import httpx


class MarzbanClient:
    def __init__(self, url: str, username: str, password: str, inbound_tag: str = "VLESS Reality"):
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.inbound_tag = inbound_tag
        self._token: Optional[str] = None
        self._token_expires: float = 0.0
        # retries=3 покрывает транзитные DNS/connect-сбои на bothost
        transport = httpx.AsyncHTTPTransport(retries=3, verify=True)
        self._client = httpx.AsyncClient(transport=transport, timeout=20)

    async def close(self) -> None:
        await self._client.aclose()

    async def _auth(self) -> None:
        if self._token and time.time() < self._token_expires - 60:
            return
        r = await self._client.post(
            f"{self.url}/api/admin/token",
            data={"username": self.username, "password": self.password},
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + 60 * 60 * 23

    async def _headers(self) -> dict[str, str]:
        await self._auth()
        return {"Authorization": f"Bearer {self._token}"}

    async def create_user(self, username: str, expire_ts: int) -> dict:
        body = {
            "username": username,
            "proxies": {"vless": {"flow": "xtls-rprx-vision"}},
            "inbounds": {"vless": [self.inbound_tag]},
            "expire": expire_ts,
            "data_limit": 0,
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
        }
        r = await self._client.post(f"{self.url}/api/user", headers=await self._headers(), json=body)
        r.raise_for_status()
        return r.json()

    async def get_user(self, username: str) -> Optional[dict]:
        r = await self._client.get(f"{self.url}/api/user/{username}", headers=await self._headers())
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    async def set_expire(self, username: str, new_expire_ts: int) -> dict:
        body = {"expire": new_expire_ts, "status": "active"}
        r = await self._client.put(f"{self.url}/api/user/{username}", headers=await self._headers(), json=body)
        r.raise_for_status()
        return r.json()

    def normalize_sub_url(self, sub_url: str) -> str:
        if not sub_url:
            return ""
        if sub_url.startswith("http"):
            return sub_url
        return f"{self.url}{sub_url}"
