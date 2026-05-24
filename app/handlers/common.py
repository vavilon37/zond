from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from ..access import format_subscription_message, grant_days
from ..db import session
from ..keyboards import BTN_HELP, main_menu
from ..marzban import MarzbanClient
from ..models import User
from ..plans import REFERRAL_BONUS_DAYS, TRIAL_DAYS

router = Router()

WELCOME = (
    "👋 <b>Zond VPN</b>\n\n"
    "🔐 VLESS + Reality — обход DPI, маскировка под TLS\n"
    "🚀 100 Mbit/s, безлимитный трафик\n"
    "💻 Приложение <b>HAPP</b> — iOS, Android, Windows, macOS\n\n"
    "Используй кнопки внизу 👇"
)

HELP_TEXT = (
    "ℹ <b>Установка HAPP и подключение</b>\n\n"
    "<b>📱 iPhone (iOS):</b>\n"
    "1. Открой App Store, найди <b>Happ</b> и установи\n"
    "2. В этом боте → «📋 Моя подписка» → скопируй ссылку-подписку\n"
    "3. Запусти Happ\n"
    "4. Нажми <b>+</b> в правом верхнем углу → «<b>Add from clipboard</b>» "
    "(или «Import» → вставь ссылку)\n"
    "5. Подписка появится в списке\n"
    "6. Нажми на ползунок подключения. При первом запуске разреши установку "
    "VPN-профиля в настройках iOS (подтверждай Touch ID / Face ID)\n"
    "7. Готово — VPN активен\n\n"
    "<b>🤖 Android:</b>\n"
    "1. Установи <b>Happ</b> из Google Play или RuStore "
    "(если в маркетах не находишь — поиск «Happ VPN apk»)\n"
    "2. В боте → «📋 Моя подписка» → скопируй ссылку-подписку\n"
    "3. Запусти Happ\n"
    "4. Нажми <b>+</b> → «<b>Add from clipboard</b>» (или «Import» → вставь URL)\n"
    "5. Подписка добавится\n"
    "6. Жми на ползунок подключения. Разреши VPN-соединение в системном диалоге\n"
    "7. Готово\n\n"
    "<b>🪟 Windows:</b>\n"
    "1. Скачай <b>Happ для Windows</b> с официального сайта <b>happ.su</b> "
    "(там же есть Microsoft Store-версия)\n"
    "2. Установи и запусти\n"
    "3. В боте → «📋 Моя подписка» → скопируй ссылку-подписку\n"
    "4. В Happ нажми <b>+</b> → «<b>Import from clipboard</b>» "
    "(или «Add subscription» → вставь URL)\n"
    "5. Включи подключение тумблером сверху\n"
    "6. В первый раз Windows спросит разрешение — подтверди\n\n"
    "<b>🍎 macOS:</b>\n"
    "• Для Apple Silicon (M1/M2/M3/M4) — поставь <b>Happ</b> "
    "из App Store, тот же что для iPhone (вкладка «iPhone и iPad Apps»)\n"
    "• Для Intel-Mac — скачай <b>Happ для macOS</b> с happ.su\n"
    "Дальше как в Windows: открыть, скопировать ссылку в боте → "
    "«+» → «Import from clipboard» → включить тумблер\n\n"
    "<b>💡 Если не подключается:</b>\n"
    "• Проверь что подписка в списке (не пустая, есть хотя бы один сервер)\n"
    "• Попробуй переподключиться (выкл/вкл)\n"
    "• В Happ открой подписку → «Update» — обновит конфиги\n"
    "• Не помогло — пиши админу\n\n"
    "🎁 <b>Бонусы в меню:</b>\n"
    "• «🎁 Пригласить друга» — +3 дня тебе и другу при первом запуске им бота по твоей ссылке\n\n"
    "Тарифы: <b>1 месяц = 200₽</b> или <b>~2 USDT</b>"
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
async def cmd_start(
    message: Message,
    command: CommandObject,
    marzban: MarzbanClient,
    bot: Bot,
    state: FSMContext,
) -> None:
    await state.clear()
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
                from datetime import datetime as _dt
                ref_expire_ts = ref_mz.get("expire") or 0
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


@router.message(F.text == BTN_HELP)
async def help_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(HELP_TEXT, reply_markup=main_menu())
