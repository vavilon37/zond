from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..keyboards import payment_methods_kb, plans_kb
from ..plans import get_plan

router = Router()


@router.callback_query(F.data == "buy")
async def show_plans(cb: CallbackQuery) -> None:
    await cb.message.edit_text("Выбери тариф:", reply_markup=plans_kb())
    await cb.answer()


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
