from typing import Optional

import httpx

CRYPTOBOT_URL = "https://pay.crypt.bot/api"


class CryptoBotClient:
    def __init__(self, token: str):
        self.token = token
        self._client = httpx.AsyncClient(timeout=20)

    async def close(self) -> None:
        await self._client.aclose()

    async def _post(self, method: str, **kwargs) -> dict:
        r = await self._client.post(
            f"{CRYPTOBOT_URL}/{method}",
            headers={"Crypto-Pay-API-Token": self.token},
            json=kwargs,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"CryptoBot error: {data}")
        return data["result"]

    async def create_invoice(self, amount_usdt: float, description: str, payload: str) -> dict:
        return await self._post(
            "createInvoice",
            asset="USDT",
            amount=f"{amount_usdt:.2f}",
            description=description,
            payload=payload,
            expires_in=3600,
        )

    async def get_invoice(self, invoice_id: int) -> Optional[dict]:
        result = await self._post("getInvoices", invoice_ids=[invoice_id])
        items = result.get("items", [])
        return items[0] if items else None
