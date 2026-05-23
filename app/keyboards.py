from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .plans import PLANS

BTN_BUY = "🛒 Купить VPN"
BTN_SUBS = "📋 Моя подписка"
BTN_REFER = "🎁 Пригласить друга"
BTN_PROMO = "🎟 Промокод"
BTN_HELP = "❓ Помощь"

MENU_TEXTS = {BTN_BUY, BTN_SUBS, BTN_REFER, BTN_PROMO, BTN_HELP}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BUY)],
            [KeyboardButton(text=BTN_SUBS), KeyboardButton(text=BTN_REFER)],
            [KeyboardButton(text=BTN_PROMO), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def plans_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{p.title} — {p.price_rub}₽ / {p.price_usdt} USDT",
                              callback_data=f"choose_plan:{p.id}")]
        for p in PLANS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_methods_kb(plan_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Крипта (USDT)", callback_data=f"pay_crypto:{plan_id}")],
        [InlineKeyboardButton(text="🏦 СБП (рубли)", callback_data=f"pay_sbp:{plan_id}")],
    ])


def admin_sbp_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_sbp_ok:{order_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_sbp_no:{order_id}"),
    ]])
