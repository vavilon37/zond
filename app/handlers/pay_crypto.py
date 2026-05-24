import logging
import secrets
from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select, update

from ..access import format_subscription_message, grant_or_extend
from ..cryptobot import CryptoBotClient
from ..db import session
from ..marzban import MarzbanClient
from ..models import Order
from ..plans import get_plan

router = Router()
log = logging.getLogger(__name__)


async def _claim_order(order_id: int) -> bool:
    """Atomically move order pending → paid. Returns True if we won the claim."""
    async with session() as s:
        res = await s.execute(
            update(Order)
            .where(Order.id == order_id, Order.status == "pending")
            .values(status="paid", paid_at=datetime.utcnow())
        )
        await s.commit()
        return res.rowcount == 1


async def _rollback_order(order_id: int) -> None:
    """Revert order from paid back to pending — used when Marzban grant fails."""
    async with session() as s:
        await s.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status="pending", paid_at=None)
        )
        await s.commit()


@router.callback_query(F.data.startswith("pay_crypto:"))
async def pay_crypto(cb: CallbackQuery, cryptobot: CryptoBotClient) -> None:
    plan_id = cb.data.split(":", 1)[1]
    plan = get_plan(plan_id)
    if not plan:
        await cb.answer("Тариф не найден", show_alert=True)
        return

    payload = f"tg:{cb.from_user.id}:{plan_id}:{secrets.token_hex(6)}"
    invoice = await cryptobot.create_invoice(
        amount_usdt=plan.price_usdt,
        description=f"Zond VPN — {plan.title}",
        payload=payload,
    )

    async with session() as s:
        order = Order(
            tg_id=cb.from_user.id,
            plan_id=plan_id,
            method="crypto",
            status="pending",
            amount=plan.price_usdt,
            external_id=str(invoice["invoice_id"]),
        )
        s.add(order)
        await s.commit()
        order_id = order.id

    text = (
        f"💎 <b>Оплата криптой</b>\n\n"
        f"Сумма: <b>{plan.price_usdt} USDT</b>\n"
        f"Срок: {plan.days} дней\n\n"
        f"1. Жми «Оплатить» — откроется CryptoBot\n"
        f"2. Оплати любой доступной криптой\n"
        f"3. Вернись в бот и нажми «Проверить оплату»\n\n"
        f"Инвойс активен 60 минут."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=invoice["pay_url"])],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_crypto:{order_id}")],
    ])
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("check_crypto:"))
async def check_crypto(cb: CallbackQuery, cryptobot: CryptoBotClient, marzban: MarzbanClient) -> None:
    order_id = int(cb.data.split(":", 1)[1])

    async with session() as s:
        order = (await s.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()

    if not order:
        await cb.answer("Заказ не найден", show_alert=True)
        return
    if order.status == "paid":
        await cb.answer("Этот заказ уже оплачен", show_alert=True)
        return
    if order.status != "pending":
        await cb.answer(f"Заказ в статусе «{order.status}» — создай новый.", show_alert=True)
        return

    # Check invoice status BEFORE claiming (don't lock the order if not paid)
    try:
        invoice = await cryptobot.get_invoice(int(order.external_id))
    except Exception as e:
        await cb.answer(f"CryptoBot недоступен ({type(e).__name__}). Попробуй позже.", show_alert=True)
        return

    if not invoice or invoice.get("status") != "paid":
        await cb.answer("Оплата ещё не пришла. Подожди минутку и попробуй снова.", show_alert=True)
        return

    # Atomic claim: only one click wins
    if not await _claim_order(order_id):
        await cb.answer("Заказ уже обрабатывается. Подожди.", show_alert=True)
        return

    plan = get_plan(order.plan_id)
    if not plan:
        await _rollback_order(order_id)
        await cb.answer("Тариф не найден в коде — напиши @yodealer", show_alert=True)
        return

    # Now grant in Marzban. If it fails, rollback so user can retry.
    try:
        mz_user = await grant_or_extend(cb.from_user.id, cb.from_user.username, plan, marzban)
    except Exception as e:
        log.exception("Marzban grant failed for order %s", order_id)
        await _rollback_order(order_id)
        await cb.answer(
            f"VPN-сервер недоступен ({type(e).__name__}). Жми «Проверить оплату» ещё раз через минуту.",
            show_alert=True,
        )
        return

    await cb.message.edit_text(format_subscription_message(mz_user, marzban))
    await cb.answer("Оплата подтверждена!")
