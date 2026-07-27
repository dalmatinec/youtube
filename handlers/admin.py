from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import config
import database as db
import queue_manager
import texts

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("setchannel"))
async def cmd_setchannel(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer(
            "Использование: /setchannel <@username или -100ID> [ссылка-приглашение, если канал приватный]"
        )
        return
    channel = parts[1]
    link = parts[2] if len(parts) > 2 else (
        f"https://t.me/{channel.lstrip('@')}" if channel.startswith("@") else None
    )
    if not link:
        await message.answer("Для приватного канала/группы укажи ссылку-приглашение вторым аргументом.")
        return
    db.set_setting("mandatory_channel", channel)
    db.set_setting("mandatory_channel_link", link)
    await message.answer(f"Обязательный канал установлен: {channel}\nСсылка: {link}")


@router.message(Command("unsetchannel"))
async def cmd_unsetchannel(message: Message):
    if not _is_admin(message.from_user.id):
        return
    db.set_setting("mandatory_channel", "")
    await message.answer("Обязательная подписка отключена.")


@router.message(Command("grant"))
async def cmd_grant(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /grant <user_id> <дней>")
        return
    try:
        target_id, days = int(parts[1]), int(parts[2])
    except ValueError:
        await message.answer("user_id и дни должны быть числами.")
        return
    new_expiry = db.grant_premium(target_id, days)
    await message.answer(f"Premium для {target_id} продлён до {new_expiry.strftime('%d.%m.%Y %H:%M')} UTC")
    try:
        await message.bot.send_message(target_id, texts.PREMIUM_GRANTED_NOTICE.format(days=days))
    except Exception:
        pass


@router.message(Command("revoke"))
async def cmd_revoke(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /revoke <user_id>")
        return
    db.revoke_premium(int(parts[1]))
    await message.answer("Premium снят.")


@router.message(Command("adminstats"))
async def cmd_adminstats(message: Message):
    if not _is_admin(message.from_user.id):
        return
    stats = db.global_stats()
    text = (
        f"Юзеров: {stats['users']}\nСкачиваний всего: {stats['downloads']}\n"
        f"Premium активно: {len(db.premium_user_ids())}\nВ очереди сейчас: {queue_manager.queue_size()}\n"
    )
    for platform, count in stats["by_platform"].items():
        text += f"  • {platform}: {count}\n"
    await message.answer(text)
