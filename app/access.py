from datetime import datetime

from sqlalchemy import select

from .db import session
from .marzban import MarzbanClient
from .models import User
from .plans import Plan


async def _get_or_create_user(tg_id: int, tg_username: str | None) -> str:
    async with session() as s:
        user = (await s.execute(select(User).where(User.tg_id == tg_id))).scalar_one_or_none()
        if user is None:
            user = User(
                tg_id=tg_id,
                username=tg_username,
                marzban_username=f"tg{tg_id}",
            )
            s.add(user)
            await s.commit()
            await s.refresh(user)
        return user.marzban_username


async def grant_days(tg_id: int, tg_username: str | None, days: int, marzban: MarzbanClient) -> dict:
    marzban_username = await _get_or_create_user(tg_id, tg_username)
    existing = await marzban.get_user(marzban_username)
    now_ts = int(datetime.utcnow().timestamp())
    if existing is None:
        expire_ts = now_ts + days * 86400
        return await marzban.create_user(marzban_username, expire_ts)
    current_expire = existing.get("expire") or 0
    base = max(current_expire, now_ts)
    new_expire = base + days * 86400
    return await marzban.set_expire(marzban_username, new_expire)


async def grant_or_extend(tg_id: int, tg_username: str | None, plan: Plan, marzban: MarzbanClient) -> dict:
    return await grant_days(tg_id, tg_username, plan.days, marzban)


def format_subscription_message(mz_user: dict, marzban: MarzbanClient, header: str = "✅ Доступ выдан!") -> str:
    sub_url = marzban.normalize_sub_url(mz_user.get("subscription_url", ""))
    expire_ts = mz_user.get("expire") or 0
    expire_str = datetime.fromtimestamp(expire_ts).strftime("%Y-%m-%d") if expire_ts else "бессрочно"
    return (
        f"{header}\n\n"
        f"📅 Действует до: <b>{expire_str}</b>\n\n"
        f"🔗 Ссылка-подписка (импортируй в клиент):\n"
        f"<code>{sub_url}</code>\n\n"
        f"📱 Клиенты: <b>Hiddify</b>, <b>v2rayTun</b>, <b>Streisand</b>"
    )
