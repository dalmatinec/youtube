import asyncio
import os

from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, Message

import config
import database as db
import downloader as dl
import keyboards as kb
import queue_manager
import subscription
from handlers.start import show_subscribe_gate

router = Router()

# user_id -> ссылка, ожидающая выбора качества (только для YouTube)
pending_urls: dict[int, str] = {}


def is_supported_link(text: str) -> bool:
    return dl.detect_platform(text) != "unknown"


@router.message(F.text)
async def handle_link(message: Message):
    db.register_user(message.from_user.id, message.from_user.username)

    if not await subscription.is_subscribed(message.bot, message.from_user.id):
        await show_subscribe_gate(message)
        return

    url = message.text.strip()
    if not is_supported_link(url):
        await message.answer("Не вижу тут ссылку на YouTube/TikTok/Instagram 🤔")
        return

    premium = db.is_premium(message.from_user.id)
    if not premium and db.downloads_last_24h(message.from_user.id) >= config.DAILY_LIMIT:
        await message.answer(
            f"Лимит {config.DAILY_LIMIT} скачиваний в сутки исчерпан.\n"
            f"⭐ /premium — снять лимит и получить приоритет в очереди."
        )
        return

    platform = dl.detect_platform(url)

    if platform == "youtube":
        wait_msg = await message.answer("Смотрю доступные качества...")
        try:
            info = await asyncio.to_thread(dl.probe, url)
        except Exception as e:
            await wait_msg.edit_text(f"Не смог обработать ссылку: {e}")
            return

        qualities = dl.list_video_qualities(info)[:6]
        pending_urls[message.from_user.id] = url
        await wait_msg.edit_text("Выбери качество:", reply_markup=kb.quality_kb(qualities))
        return

    status = await message.answer("Качаю... ⏳")
    await do_download(status, message.from_user.id, url, platform, format_selector=None, audio_only=False)


@router.callback_query(F.data.startswith("q_"))
async def handle_quality_choice(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = pending_urls.pop(user_id, None)
    if not url:
        await callback.answer("Ссылка устарела, пришли заново", show_alert=True)
        return

    choice = callback.data[2:]
    await callback.answer()
    await callback.message.edit_text("Качаю... ⏳")

    if choice == "audio":
        await do_download(callback.message, user_id, url, "youtube", format_selector=None, audio_only=True)
    else:
        await do_download(callback.message, user_id, url, "youtube", format_selector=choice, audio_only=False)


async def do_download(status_message: Message, user_id: int, url: str, platform: str,
                       format_selector: str | None, audio_only: bool):
    priority = queue_manager.PRIORITY_PREMIUM if db.is_premium(user_id) else queue_manager.PRIORITY_FREE

    ahead = queue_manager.queue_size()
    if ahead > 0:
        await status_message.answer(f"📋 В очереди перед тобой: {ahead}. Ждём...")

    coro = asyncio.to_thread(dl.download, url, format_selector, audio_only)
    fut = await queue_manager.submit(priority, coro)

    try:
        files = await fut
    except Exception as e:
        await status_message.answer(f"Не получилось скачать: {e}")
        return

    if not files:
        await status_message.answer("Файл не найден после скачивания 😕")
        return

    db.log_download(user_id, platform, url)

    oversized = 0
    for f in files:
        size_mb = os.path.getsize(f["path"]) / 1024 / 1024
        if size_mb > config.MAX_TELEGRAM_FILE_MB:
            oversized += 1
            os.remove(f["path"])
            continue

        input_file = FSInputFile(f["path"])
        try:
            if f["type"] == "video":
                await status_message.answer_video(input_file)
            elif f["type"] == "photo":
                await status_message.answer_photo(input_file)
            elif f["type"] == "audio":
                await status_message.answer_audio(input_file)
        finally:
            os.remove(f["path"])

    if oversized:
        await status_message.answer(
            f"{oversized} файл(ов) больше {config.MAX_TELEGRAM_FILE_MB}МБ — обычный Bot API их не пропускает."
        )
