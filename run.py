import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import load_config
from app.cryptobot import CryptoBotClient
from app.db import create_tables, init_db
from app.handlers import ROUTERS
from app.marzban import MarzbanClient


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = load_config()
    init_db(config.db_path)
    await create_tables()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    marzban = MarzbanClient(
        url=config.marzban_url,
        username=config.marzban_username,
        password=config.marzban_password,
        inbound_tag=config.marzban_inbound_tag,
    )
    cryptobot = CryptoBotClient(token=config.cryptobot_token)

    me = await bot.get_me()
    bot_username = me.username

    dp = Dispatcher(storage=MemoryStorage())
    dp["config"] = config
    dp["marzban"] = marzban
    dp["cryptobot"] = cryptobot
    dp["bot_username"] = bot_username

    for r in ROUTERS:
        dp.include_router(r)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Bot started as @%s", bot_username)
        await dp.start_polling(bot)
    finally:
        await marzban.close()
        await cryptobot.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
