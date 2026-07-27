from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
import texts

# Цвет кнопок появился в Bot API 9.4 (09.02.2026): style = "primary"(синий) / "success"(зелёный) / "danger"(красный)
# icon_custom_emoji_id — иконка-эмодзи прямо на кнопке (нужен Telegram Premium у бота); сейчас None-заглушки,
# как только будут ID кастомных эмодзи — просто впиши их сюда.

BACK_STYLE = "danger"       # "Назад" всегда красная
ACTION_STYLE = "success"    # обычные действия — зелёные (можно поменять на "primary" для синих)

ICON_SUBSCRIBE = None
ICON_CHECK = None
ICON_STARS = None
ICON_MANUAL = None
ICON_BACK = None


def subscribe_gate_kb(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=texts.SUBSCRIBE_JOIN_BTN, url=link,
                style=ACTION_STYLE, icon_custom_emoji_id=ICON_SUBSCRIBE,
            )],
            [InlineKeyboardButton(
                text=texts.SUBSCRIBE_CHECK_BTN, callback_data="check_sub",
                style=ACTION_STYLE, icon_custom_emoji_id=ICON_CHECK,
            )],
        ]
    )


def premium_offer_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=texts.BUY_STARS_BTN.format(price=config.STARS_PRICE),
                callback_data="buy_stars",
                style=ACTION_STYLE, icon_custom_emoji_id=ICON_STARS,
            )],
            [InlineKeyboardButton(
                text=texts.BUY_MANUAL_BTN, callback_data="buy_manual",
                style=ACTION_STYLE, icon_custom_emoji_id=ICON_MANUAL,
            )],
        ]
    )


def quality_kb(qualities: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for q in qualities:
        row.append(InlineKeyboardButton(
            text=f"{q['height']}p" + (f" (~{q['filesize'] // 1024 // 1024}МБ)" if q["filesize"] else ""),
            callback_data=f"q_{q['format_id']}",
            style=ACTION_STYLE,
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(
        text="🎵 Только аудио (mp3)", callback_data="q_audio", style=ACTION_STYLE,
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_button(callback_data: str = "back") -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="🔙 Назад", callback_data=callback_data,
        style=BACK_STYLE, icon_custom_emoji_id=ICON_BACK,
    )
