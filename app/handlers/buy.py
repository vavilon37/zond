from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..keyboards import BTN_BUY, payment_methods_kb, plans_kb
from ..plans import get_plan

router = Router()


@router.message(F.text == BTN_BUY)
async def show_plans(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Выбери тариф:", reply_markup=plans_kb())


@router.callback_query(F.data.startswith("choose_plan:"))
async def choose_plan(cb: CallbackQuery) -> None:
    plan_id = cb.data.split(":", 1)[1]
    plan = get_plan(plan_id)
    if not plan:
        await cb.answer("Тариф не найден", show_alert=True)
        return
    text = (
        f"📦 <b>{plan.title}</b>\n\n"
        f"💰 Цена: <b>{plan.price_rub}₽</b> или <b>~{plan.price_usdt} USDT</b>\n"
        f"⏱ Срок: {plan.days} дней\n"
        f"📊 Трафик: безлимит\n\n"
        f"Способ оплаты:"
    )
    await cb.message.edit_text(text, reply_markup=payment_methods_kb(plan_id))
    await cb.answer()
