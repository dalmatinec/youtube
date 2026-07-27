import asyncio
import logging

from aiogram import Bot, Dispatcher

import config
import database as db
import payments
import queue_manager
from handlers import admin, broadcast, download, premium, start, stats

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Порядок важен: сначала конкретные команды/состояния, download.router — последний,
# так как в нём общий обработчик F.text (ловит ссылки).
dp.include_router(start.router)
dp.include_router(stats.router)
dp.include_router(premium.router)
dp.include_router(admin.router)
dp.include_router(payments.router)
dp.include_router(broadcast.router)
dp.include_router(download.router)


async def main():
    db.init_db()
    queue_manager.start_workers(config.CONCURRENT_DOWNLOADS)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
