from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from ..access import format_subscription_message, grant_days
from ..db import session
from ..keyboards import main_menu
from ..marzban import MarzbanClient
from ..models import User
from ..plans import REFERRAL_BONUS_DAYS, TRIAL_DAYS

router = Router()

WELCOME = (
    "👋 <b>Zond VPN</b>\n\n"
    "🔐 VLESS + Reality — обход DPI, маскировка под TLS\n"
    "🌍 Сервер в Нидерландах\n"
    "🚀 100 Mbit/s, безлимитный трафик\n\n"
    "Выбери действие:"
)


def _parse_referrer(args: str | None, self_tg_id: int) -> int | None:
    if not args:
        return None
    args = args.strip()
    if not args.startswith("ref"):
        return None
    try:
        ref_id = int(args[3:])
    except ValueError:
        return None
    if ref_id == self_tg_id:
        return None
    return ref_id


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, marzban: MarzbanClient, bot: Bot) -> None:
    tg_id = message.from_user.id
    tg_username = message.from_user.username
    referrer_tg_id = _parse_referrer(command.args, tg_id)

    async with session() as s:
        user = (await s.execute(select(User).where(User.tg_id == tg_id))).scalar_one_or_none()
        is_new = user is None

        if is_new:
            valid_referrer = None
            if referrer_tg_id is not None:
                ref = (await s.execute(
                    select(User).where(User.tg_id == referrer_tg_id)
                )).scalar_one_or_none()
                if ref is not None:
                    valid_referrer = referrer_tg_id

            user = User(
                tg_id=tg_id,
                username=tg_username,
                marzban_username=f"tg{tg_id}",
                trial_granted=False,
                referrer_tg_id=valid_referrer,
            )
            s.add(user)
            await s.commit()
            await s.refresh(user)
        else:
            valid_referrer = user.referrer_tg_id

        grant_trial_now = not user.trial_granted
        if grant_trial_now:
            user.trial_granted = True
            await s.commit()

    if grant_trial_now:
        days = TRIAL_DAYS + (REFERRAL_BONUS_DAYS if valid_referrer else 0)
        mz_user = await grant_days(tg_id, tg_username, days, marzban)

        if valid_referrer:
            header = (
                f"🎁 <b>Пробный период активирован!</b>\n"
                f"<i>+{REFERRAL_BONUS_DAYS} дня бонуса за приглашение от друга</i>"
            )
        else:
            header = "🎁 <b>Пробный период активирован!</b>"

        await message.answer(format_subscription_message(mz_user, marzban, header=header))

        if valid_referrer:
            try:
                ref_mz = await grant_days(valid_referrer, None, REFERRAL_BONUS_DAYS, marzban)
                ref_expire_ts = ref_mz.get("expire") or 0
                from datetime import datetime as _dt
                ref_expire_str = (
                    _dt.fromtimestamp(ref_expire_ts).strftime("%Y-%m-%d")
                    if ref_expire_ts else "бессрочно"
                )
                await bot.send_message(
                    valid_referrer,
                    f"🎉 По твоей ссылке зарегистрировался новый юзер!\n"
                    f"Тебе начислено <b>+{REFERRAL_BONUS_DAYS} дня</b>.\n"
                    f"📅 Подписка теперь до: <b>{ref_expire_str}</b>"
                )
            except Exception:
                pass

    await message.answer(WELCOME, reply_markup=main_menu())


@router.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text(WELCOME, reply_markup=main_menu())
    await cb.answer()


@router.callback_query(F.data == "help")
async def help_cb(cb: CallbackQuery) -> None:
    text = (
        "ℹ <b>Как пользоваться</b>\n\n"
        "1. Получи пробные дни (автоматом при /start)\n"
        "2. Или купи подписку — 1 месяц за 200₽\n"
        "3. Получи ссылку-подписку\n"
        "4. Поставь клиент: <b>Hiddify</b> / <b>v2rayTun</b> / <b>Streisand</b>\n"
        "5. В клиенте: «Добавить из URL» → вставь ссылку\n"
        "6. Подключайся\n\n"
        f"🎁 <b>Бонусы:</b>\n"
        f"• Приглашай друзей — по +3 дня вам обоим\n"
        f"• Промокод <code>zondvpn</code> — 7 бесплатных дней\n\n"
        "Вопросы — пиши админу."
    )
    await cb.message.edit_text(text, reply_markup=main_menu())
    await cb.answer()
