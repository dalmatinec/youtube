from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import config
import database as db
import keyboards as kb
import payments
import texts

router = Router()


@router.message(Command("premium"))
async def cmd_premium(message: Message):
    expiry = db.premium_expiry(message.from_user.id)
    if expiry and expiry > datetime.now(timezone.utc):
        await message.answer(texts.PREMIUM_INFO_ACTIVE.format(expiry=expiry.strftime("%d.%m.%Y %H:%M")))
        return
    await message.answer(texts.PREMIUM_INFO_NONE.format(days=config.PREMIUM_DAYS), reply_markup=kb.premium_offer_kb())


@router.callback_query(F.data == "buy_stars")
async def cb_buy_stars(callback: CallbackQuery):
    await callback.answer()
    await payments.send_stars_invoice(callback.bot, callback.from_user.id)


@router.callback_query(F.data == "buy_manual")
async def cb_buy_manual(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        texts.MANUAL_PAYMENT_TEXT.format(contact=config.ADMIN_CONTACT, user_id=callback.from_user.id)
    )
