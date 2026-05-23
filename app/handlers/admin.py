from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from ..access import format_subscription_message, grant_or_extend
from ..config import Config
from ..db import session
from ..keyboards import admin_sbp_kb
from ..marzban import MarzbanClient
from ..models import Order, User
from ..plans import get_plan

router = Router()


def is_admin(uid: int, config: Config) -> bool:
    return uid in config.admin_ids


@router.message(Command("admin"))
async def admin_root(message: Message, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    async with session() as s:
        total_users = (await s.execute(select(func.count(User.id)))).scalar() or 0
        paid_orders = (await s.execute(
            select(func.count(Order.id)).where(Order.status == "paid")
        )).scalar() or 0
        pending_sbp = (await s.execute(
            select(func.count(Order.id)).where(Order.status == "pending", Order.method == "sbp")
        )).scalar() or 0
        revenue_rub = (await s.execute(
            select(func.sum(Order.amount)).where(Order.status == "paid", Order.method == "sbp")
        )).scalar() or 0.0
        revenue_usdt = (await s.execute(
            select(func.sum(Order.amount)).where(Order.status == "paid", Order.method == "crypto")
        )).scalar() or 0.0

    text = (
        f"⚙ <b>Админка</b>\n\n"
        f"👥 Юзеров в БД: <b>{total_users}</b>\n"
        f"💰 Оплачено заказов: <b>{paid_orders}</b>\n"
        f"⏳ Ждут подтверждения (СБП): <b>{pending_sbp}</b>\n\n"
        f"💵 Выручка СБП: <b>{revenue_rub:.0f}₽</b>\n"
        f"💎 Выручка крипты: <b>{revenue_usdt:.2f} USDT</b>\n\n"
        f"<b>Команды:</b>\n"
        f"/pending — заявки СБП на подтверждение\n"
        f"/orders — последние 10 заказов\n"
        f"/grant &lt;tg_id&gt; &lt;plan_id&gt; — выдать вручную"
    )
    await message.answer(text)


@router.message(Command("pending"))
async def pending(message: Message, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    async with session() as s:
        orders = (await s.execute(
            select(Order)
            .where(Order.status == "pending", Order.method == "sbp")
            .order_by(Order.created_at.desc())
            .limit(20)
        )).scalars().all()

    if not orders:
        await message.answer("Нет ожидающих СБП-заявок.")
        return

    for o in orders:
        plan = get_plan(o.plan_id)
        plan_title = plan.title if plan else o.plan_id
        await message.answer(
            f"#{o.id} | tg:<code>{o.tg_id}</code> | {plan_title} | "
            f"<b>{o.amount:.0f}₽</b> | {o.created_at:%Y-%m-%d %H:%M}",
            reply_markup=admin_sbp_kb(o.id),
        )


@router.message(Command("orders"))
async def orders(message: Message, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    async with session() as s:
        rows = (await s.execute(
            select(Order).order_by(Order.created_at.desc()).limit(10)
        )).scalars().all()

    if not rows:
        await message.answer("Заказов нет.")
        return

    lines = ["<b>Последние заказы:</b>\n"]
    for o in rows:
        emoji = {"paid": "✅", "pending": "⏳", "rejected": "❌"}.get(o.status, "❓")
        unit = "USDT" if o.method == "crypto" else "₽"
        lines.append(
            f"{emoji} #{o.id} | tg:<code>{o.tg_id}</code> | {o.method} | "
            f"{o.plan_id} | {o.amount:.2f}{unit} | {o.created_at:%m-%d %H:%M}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("grant"))
async def grant_manual(message: Message, config: Config, marzban: MarzbanClient, bot: Bot) -> None:
    if not is_admin(message.from_user.id, config):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Использование: /grant &lt;tg_id&gt; &lt;plan_id&gt;\nНапример: /grant 123456789 1m")
        return
    try:
        tg_id = int(parts[1])
    except ValueError:
        await message.answer("tg_id должен быть числом")
        return
    plan = get_plan(parts[2])
    if not plan:
        await message.answer(f"План не найден. Доступные: 1m, 3m, 6m")
        return

    mz_user = await grant_or_extend(tg_id, None, plan, marzban)
    text = format_subscription_message(mz_user, marzban)
    try:
        await bot.send_message(tg_id, text)
        await message.answer(f"✅ Выдано юзеру <code>{tg_id}</code>, план {plan.title}")
    except Exception as e:
        await message.answer(f"Доступ выдан, но не смог уведомить юзера: {e}")


@router.callback_query(F.data.startswith("admin_sbp_ok:"))
async def admin_sbp_ok(cb: CallbackQuery, bot: Bot, config: Config, marzban: MarzbanClient) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer()
        return
    order_id = int(cb.data.split(":", 1)[1])

    async with session() as s:
        order = (await s.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
        if not order or order.status != "pending":
            await cb.answer("Заказ уже обработан", show_alert=True)
            return
        order.status = "paid"
        order.paid_at = datetime.utcnow()
        tg_id = order.tg_id
        plan_id = order.plan_id
        await s.commit()

    plan = get_plan(plan_id)
    if not plan:
        await cb.answer("План не найден в коде, проверь plans.py", show_alert=True)
        return

    mz_user = await grant_or_extend(tg_id, None, plan, marzban)
    try:
        await bot.send_message(tg_id, format_subscription_message(mz_user, marzban))
    except Exception:
        pass

    await cb.message.edit_text(
        (cb.message.html_text or cb.message.text) + "\n\n✅ <b>Подтверждено, доступ выдан.</b>"
    )
    await cb.answer("Готово")


@router.callback_query(F.data.startswith("admin_sbp_no:"))
async def admin_sbp_no(cb: CallbackQuery, bot: Bot, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer()
        return
    order_id = int(cb.data.split(":", 1)[1])

    async with session() as s:
        order = (await s.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
        if not order:
            await cb.answer("Не найден")
            return
        if order.status != "pending":
            await cb.answer(f"Уже: {order.status}", show_alert=True)
            return
        order.status = "rejected"
        tg_id = order.tg_id
        await s.commit()

    try:
        await bot.send_message(
            tg_id,
            f"❌ Заказ #{order_id} отклонён — оплата не найдена. "
            f"Если уверен что платил — напиши админу."
        )
    except Exception:
        pass

    await cb.message.edit_text(
        (cb.message.html_text or cb.message.text) + "\n\n❌ <b>Отклонён.</b>"
    )
    await cb.answer("Отклонён")
