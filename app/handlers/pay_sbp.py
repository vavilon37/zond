from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from ..config import Config
from ..db import session
from ..keyboards import admin_sbp_kb
from ..models import Order
from ..plans import get_plan

router = Router()


@router.callback_query(F.data.startswith("pay_sbp:"))
async def pay_sbp(cb: CallbackQuery, config: Config) -> None:
    plan_id = cb.data.split(":", 1)[1]
    plan = get_plan(plan_id)
    if not plan:
        await cb.answer("Тариф не найден", show_alert=True)
        return

    async with session() as s:
        order = Order(
            tg_id=cb.from_user.id,
            plan_id=plan_id,
            method="sbp",
            status="pending",
            amount=float(plan.price_rub),
        )
        s.add(order)
        await s.commit()
        await s.refresh(order)
        order_id = order.id

    text = (
        f"🏦 <b>Оплата по СБП</b>\n\n"
        f"💰 Сумма: <b>{plan.price_rub}₽</b>\n"
        f"📅 Срок: {plan.days} дней\n\n"
        f"<b>Реквизиты:</b>\n"
        f"📱 Телефон: <code>{config.sbp_phone}</code>\n"
        f"🏦 Банк: <b>{config.sbp_bank}</b>\n"
        f"👤 Получатель: {config.sbp_name}\n\n"
        f"⚠ <b>В комментарии к переводу укажи:</b>\n"
        f"<code>order{order_id}</code>\n\n"
        f"После оплаты нажми «Я оплатил». "
        f"Админ проверит поступление и подтвердит — обычно в течение часа."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"sbp_paid:{order_id}")],
        [InlineKeyboardButton(text="◀ Отмена", callback_data="back_main")],
    ])
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("sbp_paid:"))
async def sbp_paid(cb: CallbackQuery, bot: Bot, config: Config) -> None:
    order_id = int(cb.data.split(":", 1)[1])

    async with session() as s:
        order = (await s.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
        if not order:
            await cb.answer("Заказ не найден", show_alert=True)
            return
        if order.status != "pending":
            await cb.answer(f"Статус заказа: {order.status}", show_alert=True)
            return

        plan = get_plan(order.plan_id)
        username_str = f"@{cb.from_user.username}" if cb.from_user.username else "(без username)"
        admin_text = (
            f"🆕 <b>Новый СБП-платёж</b>\n\n"
            f"Order: <code>#{order_id}</code>\n"
            f"User: {username_str} (<code>{cb.from_user.id}</code>)\n"
            f"Plan: {plan.title} ({plan.days}д)\n"
            f"Сумма: <b>{order.amount:.0f}₽</b>\n\n"
            f"Проверь приход и подтверди."
        )
        for admin_id in config.admin_ids:
            try:
                await bot.send_message(admin_id, admin_text, reply_markup=admin_sbp_kb(order_id))
            except Exception:
                pass

    await cb.message.edit_text(
        "⏳ Заявка отправлена админу.\n"
        "Когда платёж подтвердят — пришлю сюда ссылку-подписку.\n"
        "Обычно — в течение часа."
    )
    await cb.answer()
