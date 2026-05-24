# Zond VPN — Telegram-бот

Бот для продажи доступа к Marzban-VPN. Платежи: CryptoBot (USDT) и СБП (ручное подтверждение).

## Что нужно изменить перед запуском

Скопируй `.env.example` в `.env` и заполни:

```bash
cp .env.example .env
nano .env
```

**Обязательные поля:**

| Переменная | Откуда взять |
|---|---|
| `BOT_TOKEN` | @BotFather → /newbot → токен |
| `ADMIN_IDS` | Твой Telegram user id, узнать у @userinfobot. Если админов несколько — через запятую |
| `MARZBAN_URL` | URL твоей Marzban-админки, по умолчанию `https://zondvpn.duckdns.org:8000` |
| `MARZBAN_USERNAME` | Логин админа Marzban для бота. Создай отдельного: `sudo marzban cli admin create --sudo` |
| `MARZBAN_PASSWORD` | Пароль этого админа |
| `CRYPTOBOT_TOKEN` | @CryptoBot → My Apps → Create App → API Token |
| `SBP_PHONE` | Твой номер для приёма СБП-переводов |
| `SBP_BANK` | Название твоего банка (Тинькофф, Сбер и т.д.) |
| `SBP_NAME` | Имя получателя как в банке |

**Опциональные:**

- `MARZBAN_INBOUND_TAG` — тег inbound в xray_config.json. По умолчанию `VLESS Reality`. Менять только если ты переименовал inbound в Marzban
- `DB_PATH` — путь к SQLite файлу, по умолчанию `data.sqlite3` в корне проекта

## Тарифы и бонусы

- Тарифы в `app/plans.py`. Сейчас: только 1 месяц за 200₽ / 2.0 USDT
- Триал: 3 дня всем новичкам автоматически при `/start`
- Реферал: +3 дня обоим (приглашённому и пригласившему). Ссылка вида `https://t.me/<bot>?start=ref<tg_id>`
- Промокоды: в `app/promos.py`. Сейчас: `zondvpn` = 7 дней. Каждый юзер может активировать каждый код один раз

## Запуск локально

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Деплой на bothost.ru

1. Загрузи всю папку (кроме `.env` и `data.sqlite3`) на bothost
2. На bothost создай `.env` через их веб-интерфейс, заполни
3. Установить зависимости: `pip install -r requirements.txt`
4. Запустить: `python run.py`

На bothost обычно есть кнопка "Запустить" / "Restart bot" — она и работает с `python run.py`.

## Команды бота

**Для пользователей:**
- `/start` — главное меню

**Для админа** (только из ADMIN_IDS):
- `/admin` — статистика
- `/pending` — заявки СБП на подтверждение
- `/orders` — последние 10 заказов
- `/grant <tg_id> <plan_id>` — выдать тариф вручную (`plan_id = 1m`)
- `/days <tg_id> <days>` — выдать произвольное число дней

## Логика работы

**Покупка через CryptoBot:**
1. Юзер выбирает план → "Крипта"
2. Бот создаёт инвойс через CryptoBot API
3. Юзер платит через @CryptoBot
4. Юзер возвращается в бот → жмёт "Проверить оплату"
5. Бот опрашивает CryptoBot API, видит paid → создаёт юзера в Marzban → выдаёт ссылку

**Покупка через СБП:**
1. Юзер выбирает план → "СБП"
2. Бот показывает реквизиты + просит указать `order<N>` в комментарии
3. Юзер платит, жмёт "Я оплатил"
4. Админу прилетает уведомление с кнопками "Подтвердить / Отклонить"
5. Админ проверяет банковское приложение, подтверждает
6. Бот выдаёт ссылку юзеру

**Продление** — повторная покупка автоматически продлевает существующего юзера в Marzban (прибавляет дни к текущему сроку, если он ещё активен; иначе считает от сейчас).

## Структура

```
zondvpn-bot/
├── run.py                  # entry point
├── requirements.txt
├── .env.example
└── app/
    ├── config.py           # env → Config
    ├── plans.py            # тарифы (МЕНЯТЬ ЦЕНЫ ЗДЕСЬ)
    ├── db.py               # SQLAlchemy setup
    ├── models.py           # User, Order
    ├── marzban.py          # Marzban API client
    ├── cryptobot.py        # CryptoBot API client
    ├── keyboards.py        # inline keyboards
    ├── access.py           # выдача/продление доступа
    └── handlers/
        ├── common.py       # /start, помощь
        ├── buy.py          # выбор тарифа
        ├── pay_crypto.py   # CryptoBot flow
        ├── pay_sbp.py      # СБП flow
        ├── subs.py         # "Моя подписка"
        └── admin.py        # админ-команды
```

