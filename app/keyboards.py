from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .plans import PLANS


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy")],
        [InlineKeyboardButton(text="📋 Моя подписка", callback_data="my_subs")],
        [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="refer")],
        [InlineKeyboardButton(text="🎟 Промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ])


def plans_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{p.title} — {p.price_rub}₽ / {p.price_usdt} USDT",
                              callback_data=f"choose_plan:{p.id}")]
        for p in PLANS
    ]
    rows.append([InlineKeyboardButton(text="◀ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_methods_kb(plan_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Крипта (USDT)", callback_data=f"pay_crypto:{plan_id}")],
        [InlineKeyboardButton(text="🏦 СБП (рубли)", callback_data=f"pay_sbp:{plan_id}")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="buy")],
    ])


def admin_sbp_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_sbp_ok:{order_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_sbp_no:{order_id}"),
    ]])


def back_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀ В меню", callback_data="back_main"),
    ]])
