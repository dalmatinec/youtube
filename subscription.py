from aiogram import Bot

import database as db


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """True, если гейт отключён (канал не задан) или юзер состоит в канале/группе."""
    channel = db.get_setting("mandatory_channel")
    if not channel:
        return True
    try:
        member = await bot.get_chat_member(channel, user_id)
    except Exception:
        # если бот не админ в канале / канал недоступен — не блокируем юзеров из-за своей ошибки конфигурации
        return True
    return member.status not in ("left", "kicked")
