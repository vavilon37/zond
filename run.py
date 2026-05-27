import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.cleanup import cleanup_loop
from app.config import load_config
from app.cryptobot import CryptoBotClient
from app.db import create_tables, init_db
from app.handlers import ROUTERS
from app.xui import XuiClient


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
    xui = XuiClient(
        url=config.xui_url,
        base_path=config.xui_base_path,
        api_token=config.xui_api_token,
        inbound_id=config.xui_inbound_id,
        sub_base_url=config.xui_sub_base_url,
        sub_path=config.xui_sub_path,
    )
    cryptobot = CryptoBotClient(token=config.cryptobot_token)

    me = await bot.get_me()
    bot_username = me.username

    dp = Dispatcher(storage=MemoryStorage())
    dp["config"] = config
    dp["marzban"] = xui  # handlers still call it "marzban" via DI key
    dp["cryptobot"] = cryptobot
    dp["bot_username"] = bot_username

    for r in ROUTERS:
        dp.include_router(r)

    cleanup_task = asyncio.create_task(cleanup_loop())

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Bot started as @%s", bot_username)
        await dp.start_polling(bot)
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        await xui.close()
        await cryptobot.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
