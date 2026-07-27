from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
import database as db
import downloader as dl
import texts
from handlers.download import do_download

router = Router()


def _is_supported_link(text: str) -> bool:
    return dl.detect_platform(text) != "unknown"


def _promo_kb(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⬇️ В личке: выбор качества, mp3, без лимита",
            url=f"https://t.me/{bot_username}?start=group",
            style="success",
        )]
    ])


@router.message(F.text, F.chat.type.in_({"group", "supergroup"}))
async def handle_group_link(message: Message):
    url = message.text.strip()
    if not _is_supported_link(url):
        return  # обычный текст в группе игнорируем, чтобы не спамить

    db.register_user(message.from_user.id, message.from_user.username)

    if not db.is_premium(message.from_user.id) and db.downloads_last_24h(message.from_user.id) >= config.DAILY_LIMIT:
        return  # лимит исчерпан — молча игнорим в группе, а не заваливаем чат текстом

    platform = dl.detect_platform(url)
    status = await message.reply(texts.DOWNLOADING)

    # В группе — сразу лучшее качество без выбора, чтобы не захламлять чат кнопками
    await do_download(status, message.from_user.id, url, platform, format_selector=None, audio_only=False)

    me = await message.bot.get_me()
    await message.answer(
        f"👆 Скачано через @{me.username}. Хочешь выбор качества и mp3 — жми:",
        reply_markup=_promo_kb(me.username),
    )
