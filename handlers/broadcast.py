import asyncio

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
import database as db
import texts

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


class Broadcast(StatesGroup):
    content = State()
    button_text = State()
    button_url = State()
    button_color = State()
    more_buttons = State()
    audience = State()
    confirm = State()


COLOR_MAP = {"primary": "🔵 Синяя", "success": "🟢 Зелёная", "danger": "🔴 Красная"}


def _color_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"bc_color_{style}")]
                          for style, label in COLOR_MAP.items()]
    )


def _more_buttons_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить кнопку", callback_data="bc_addbtn", style="success")],
        [InlineKeyboardButton(text="✅ Готово, дальше", callback_data="bc_buttons_done", style="primary")],
    ])


def _audience_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Всем", callback_data="bc_aud_all", style="primary")],
        [InlineKeyboardButton(text="🆓 Только бесплатным (реклама)", callback_data="bc_aud_free", style="success")],
        [InlineKeyboardButton(text="⭐ Только премиум", callback_data="bc_aud_premium", style="primary")],
    ])


def _confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отправить", callback_data="bc_send", style="success")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="bc_cancel", style="danger")],
    ])


def _audience_ids(audience: str) -> list[int]:
    if audience == "free":
        return list(db.free_user_ids())
    if audience == "premium":
        return list(db.premium_user_ids())
    return db.all_user_ids()


# ---------------- сценарий ----------------

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(Broadcast.content)
    await message.answer(
        "Пришли пост для рассылки — текст, фото или видео с подписью.\n"
        "Форматирование и premium-эмодзи (если вставишь как Premium-юзер) сохранятся как есть."
    )


@router.message(StateFilter(Broadcast.content))
async def bc_content(message: Message, state: FSMContext):
    await state.update_data(src_chat_id=message.chat.id, src_message_id=message.message_id, buttons=[])
    await state.set_state(Broadcast.more_buttons)
    await message.answer("Пост принят. Добавить кнопку?", reply_markup=_more_buttons_kb())


@router.callback_query(StateFilter(Broadcast.more_buttons), F.data == "bc_addbtn")
async def bc_addbtn(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Broadcast.button_text)
    await callback.message.answer("Текст кнопки:")


@router.message(StateFilter(Broadcast.button_text))
async def bc_button_text(message: Message, state: FSMContext):
    await state.update_data(pending_btn_text=message.text)
    await state.set_state(Broadcast.button_url)
    await message.answer("Ссылка для кнопки (https://...):")


@router.message(StateFilter(Broadcast.button_url))
async def bc_button_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("Похоже, это не ссылка. Пришли ссылку, начинающуюся с http(s)://")
        return
    await state.update_data(pending_btn_url=url)
    await state.set_state(Broadcast.button_color)
    await message.answer("Выбери цвет кнопки (тапни):", reply_markup=_color_kb())


@router.callback_query(StateFilter(Broadcast.button_color), F.data.startswith("bc_color_"))
async def bc_button_color(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    style = callback.data.removeprefix("bc_color_")
    data = await state.get_data()
    buttons = data.get("buttons", [])
    buttons.append({"text": data["pending_btn_text"], "url": data["pending_btn_url"], "style": style})
    await state.update_data(buttons=buttons, pending_btn_text=None, pending_btn_url=None)
    await state.set_state(Broadcast.more_buttons)
    await callback.message.answer(
        f"Кнопка добавлена ({COLOR_MAP[style]}). Ещё одну?", reply_markup=_more_buttons_kb()
    )


@router.callback_query(StateFilter(Broadcast.more_buttons), F.data == "bc_buttons_done")
async def bc_buttons_done(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Broadcast.audience)
    await callback.message.answer("Кому отправляем?", reply_markup=_audience_kb())


@router.callback_query(StateFilter(Broadcast.audience), F.data.startswith("bc_aud_"))
async def bc_audience(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    audience = callback.data.removeprefix("bc_aud_")
    data = await state.update_data(audience=audience)
    total = len(_audience_ids(audience))
    btn_count = len(data.get("buttons", []))
    await state.set_state(Broadcast.confirm)
    await callback.message.answer(
        f"Получателей: {total}\nКнопок: {btn_count}\nАудитория: {audience}\n\nОтправляем?",
        reply_markup=_confirm_kb(),
    )


@router.callback_query(StateFilter(Broadcast.confirm), F.data == "bc_cancel")
async def bc_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.")


@router.callback_query(StateFilter(Broadcast.confirm), F.data == "bc_send")
async def bc_send(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await state.clear()

    buttons = data.get("buttons", [])
    kb_markup = None
    if buttons:
        kb_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=b["text"], url=b["url"], style=b["style"])] for b in buttons]
        )

    audience = data["audience"]
    ids = _audience_ids(audience)
    await callback.message.edit_text(texts.BROADCAST_STARTED.format(count=len(ids)))

    bot = callback.bot
    sent, failed = 0, 0
    for uid in ids:
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=data["src_chat_id"],
                message_id=data["src_message_id"],
                reply_markup=kb_markup,
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # антифлуд, ~20 сообщений/сек

    db.log_broadcast(callback.from_user.id, audience, len(ids), sent, failed)
    await callback.message.answer(f"✅ Готово.\nОтправлено: {sent}\nНе доставлено: {failed}\nВсего: {len(ids)}")


@router.message(Command("broadcasts"))
async def cmd_broadcasts(message: Message):
    if not _is_admin(message.from_user.id):
        return
    rows = db.broadcast_history()
    if not rows:
        await message.answer("Рассылок ещё не было.")
        return
    text = "Последние рассылки:\n\n"
    for audience, total, sent, failed, created_at in rows:
        text += f"{created_at[:16]} — {audience}: {sent}/{total} доставлено ({failed} ошибок)\n"
    await message.answer(text)
