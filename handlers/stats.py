from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import config
import database as db

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = db.user_stats(message.from_user.id)
    left = max(0, config.DAILY_LIMIT - db.downloads_last_24h(message.from_user.id))

    text = f"Всего скачано: {stats['total']}\n"
    for platform, count in stats["by_platform"].items():
        text += f"  • {platform}: {count}\n"

    if db.is_premium(message.from_user.id):
        text += "\n⭐ У тебя Premium — без лимита, без рекламы, приоритет в очереди."
    else:
        text += f"\nОсталось сегодня: {left}/{config.DAILY_LIMIT}"
    await message.answer(text)
