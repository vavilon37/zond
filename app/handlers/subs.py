from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from ..db import session
from ..keyboards import BTN_SUBS, main_menu
from ..marzban import MarzbanClient
from ..models import User

router = Router()


@router.message(F.text == BTN_SUBS)
async def my_subs(message: Message, marzban: MarzbanClient, state: FSMContext) -> None:
    await state.clear()

    async with session() as s:
        user = (await s.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()

    if not user:
        await message.answer(
            "У тебя пока нет подписок. Жми «🛒 Купить VPN».",
            reply_markup=main_menu(),
        )
        return

    mz_user = await marzban.get_user(user.marzban_username)
    if not mz_user:
        await message.answer(
            "Подписка не найдена на сервере — напиши админу.",
            reply_markup=main_menu(),
        )
        return

    expire_ts = mz_user.get("expire") or 0
    now_ts = int(datetime.utcnow().timestamp())
    if expire_ts and expire_ts < now_ts:
        status_emoji = "❌"
        status_text = "Истекла — продли подписку"
    else:
        status_emoji = "✅"
        status_text = "Активна"

    expire_str = datetime.fromtimestamp(expire_ts).strftime("%Y-%m-%d") if expire_ts else "бессрочно"
    used_gb = mz_user.get("used_traffic", 0) / (1024 ** 3)
    sub_url = marzban.normalize_sub_url(mz_user.get("subscription_url", ""))

    text = (
        f"📋 <b>Твоя подписка</b>\n\n"
        f"{status_emoji} {status_text}\n"
        f"📅 Действует до: <b>{expire_str}</b>\n"
        f"📊 Использовано: {used_gb:.2f} GB\n\n"
        f"🔗 Ссылка-подписка для <b>HAPP</b>:\n<code>{sub_url}</code>\n\n"
        f"Инструкция по установке — кнопка «❓ Помощь»."
    )
    await message.answer(text, reply_markup=main_menu())
