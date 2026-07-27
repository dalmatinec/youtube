from aiogram import Bot, Router, F
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery

import config
import database as db
import texts

router = Router()


async def send_stars_invoice(bot: Bot, chat_id: int):
    await bot.send_invoice(
        chat_id=chat_id,
        title="Premium подписка",
        description=f"Приоритет в очереди и без рекламы на {config.PREMIUM_DAYS} дней",
        payload=f"premium_{config.PREMIUM_DAYS}",
        currency="XTR",  # валюта Telegram Stars
        prices=[LabeledPrice(label=f"Premium {config.PREMIUM_DAYS} дней", amount=config.STARS_PRICE)],
        provider_token="",  # для Stars токен провайдера не нужен
    )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await pre_checkout_q.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    db.grant_premium(message.from_user.id, config.PREMIUM_DAYS)
    await message.answer(texts.PAYMENT_SUCCESS.format(days=config.PREMIUM_DAYS))
