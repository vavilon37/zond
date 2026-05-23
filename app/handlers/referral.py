from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import func, select

from ..db import session
from ..keyboards import back_main_kb
from ..models import User
from ..plans import REFERRAL_BONUS_DAYS, TRIAL_DAYS

router = Router()


@router.callback_query(F.data == "refer")
async def show_refer(cb: CallbackQuery, bot_username: str) -> None:
    tg_id = cb.from_user.id

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
    await cb.message.edit_text(text, reply_markup=back_main_kb())
    await cb.answer()
