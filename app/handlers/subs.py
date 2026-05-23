from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from ..db import session
from ..marzban import MarzbanClient
from ..models import User

router = Router()


@router.callback_query(F.data == "my_subs")
async def my_subs(cb: CallbackQuery, marzban: MarzbanClient) -> None:
    async with session() as s:
        user = (await s.execute(select(User).where(User.tg_id == cb.from_user.id))).scalar_one_or_none()

    if not user:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купить", callback_data="buy")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="back_main")],
        ])
        await cb.message.edit_text("У тебя пока нет подписок.", reply_markup=kb)
        await cb.answer()
        return

    mz_user = await marzban.get_user(user.marzban_username)
    if not mz_user:
        await cb.answer("Подписка не найдена в Marzban — напиши админу", show_alert=True)
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
        f"🔗 Ссылка-подписка:\n<code>{sub_url}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Продлить", callback_data="buy")],
        [InlineKeyboardButton(text="◀ В меню", callback_data="back_main")],
    ])
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()
