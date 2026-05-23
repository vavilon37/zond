from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import func, select

from ..db import session
from ..keyboards import BTN_REFER, main_menu
from ..models import User
from ..plans import REFERRAL_BONUS_DAYS, TRIAL_DAYS

router = Router()


@router.message(F.text == BTN_REFER)
async def show_refer(message: Message, bot_username: str, state: FSMContext) -> None:
    await state.clear()
    tg_id = message.from_user.id

    async with session() as s:
        invited_count = (await s.execute(
            select(func.count(User.id)).where(User.referrer_tg_id == tg_id)
        )).scalar() or 0

    ref_link = f"https://t.me/{bot_username}?start=ref{tg_id}"

    text = (
        f"🎁 <b>Приглашай друзей — получай дни</b>\n\n"
        f"<b>Условия:</b>\n"
        f"• Друг получает <b>{TRIAL_DAYS + REFERRAL_BONUS_DAYS} дней</b> "
        f"({TRIAL_DAYS} триал + {REFERRAL_BONUS_DAYS} за реферал)\n"
        f"• Ты получаешь <b>+{REFERRAL_BONUS_DAYS} дня</b> за каждого\n\n"
        f"🔗 <b>Твоя ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 Приглашено: <b>{invited_count}</b>"
    )
    await message.answer(text, reply_markup=main_menu())
