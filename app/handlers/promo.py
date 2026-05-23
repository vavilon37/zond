import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..access import format_subscription_message, grant_days
from ..db import session
from ..keyboards import back_main_kb, main_menu
from ..marzban import MarzbanClient
from ..models import PromoUse
from ..promos import get_promo_days

router = Router()
log = logging.getLogger(__name__)


class PromoStates(StatesGroup):
    waiting_code = State()


@router.callback_query(F.data == "enter_promo")
async def ask_promo(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PromoStates.waiting_code)
    log.info("Promo state set for user %s", cb.from_user.id)
    await cb.message.edit_text(
        "🎟 <b>Промокод</b>\n\nОтправь промокод сообщением:",
        reply_markup=back_main_kb(),
    )
    await cb.answer()


@router.message(StateFilter(PromoStates.waiting_code))
async def receive_promo(message: Message, state: FSMContext, marzban: MarzbanClient) -> None:
    code = (message.text or "").strip().lower()
    log.info("Promo input from %s: '%s'", message.from_user.id, code)
    await state.clear()

    bonus_days = get_promo_days(code)
    if bonus_days is None:
        await message.answer(
            "❌ Промокод не найден или истёк.",
            reply_markup=main_menu(),
        )
        return

    async with session() as s:
        already = (await s.execute(
            select(PromoUse).where(PromoUse.tg_id == message.from_user.id, PromoUse.code == code)
        )).scalar_one_or_none()
        if already:
            await message.answer(
                "⚠ Ты уже активировал этот промокод.",
                reply_markup=main_menu(),
            )
            return

    try:
        mz_user = await grant_days(
            message.from_user.id, message.from_user.username, bonus_days, marzban
        )
    except Exception as e:
        log.exception("Marzban grant failed for promo")
        await message.answer(
            f"⚠ Временная ошибка ({type(e).__name__}). Попробуй через минуту.",
            reply_markup=main_menu(),
        )
        return

    async with session() as s:
        s.add(PromoUse(tg_id=message.from_user.id, code=code))
        try:
            await s.commit()
        except IntegrityError:
            await s.rollback()

    await message.answer(
        format_subscription_message(
            mz_user, marzban,
            header=f"🎉 <b>Промокод активирован!</b>\n<i>+{bonus_days} дней к подписке</i>",
        ),
        reply_markup=main_menu(),
    )
