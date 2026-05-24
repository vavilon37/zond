"""Фоновая чистка протухших pending-заказов."""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import update

from .db import session
from .models import Order

log = logging.getLogger(__name__)


async def _cancel_stale_pending(max_age_hours: int) -> int:
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    async with session() as s:
        res = await s.execute(
            update(Order)
            .where(Order.status == "pending", Order.created_at < cutoff)
            .values(status="cancelled")
        )
        await s.commit()
        return res.rowcount or 0


async def cleanup_loop(interval_seconds: int = 3600, max_age_hours: int = 24) -> None:
    """Раз в час помечает pending-заказы старше 24 часов как cancelled."""
    while True:
        try:
            count = await _cancel_stale_pending(max_age_hours)
            if count > 0:
                log.info("Cancelled %d stale pending orders (older than %dh)", count, max_age_hours)
        except Exception:
            log.exception("cleanup_pending failed")
        await asyncio.sleep(interval_seconds)
