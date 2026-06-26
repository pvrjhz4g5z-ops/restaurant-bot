import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, Message
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json
import database as db
from config import BOT_TOKEN, ADMIN_ID, WEBAPP_URL

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await db.init_db()
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🪑 Забронювати столик",
        web_app=WebAppInfo(url=WEBAPP_URL)
    ))
    await message.answer(
        "👋 Вітаємо в нашому ресторані!\n\n"
        "Натисніть кнопку нижче, щоб обрати столик і зробити бронювання.",
        reply_markup=builder.as_markup()
    )


@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        table_name = data.get("tableName", "—")
        date = data.get("date", "—")
        time = data.get("time", "—")
        guests = data.get("guests", "—")
        name = data.get("name", "—")
        phone = data.get("phone", "—")
        note = data.get("note", "")

        booking_id = await db.save_booking(
            user_id=message.from_user.id,
            table_name=table_name,
            date=date,
            time=time,
            guests=guests,
            name=name,
            phone=phone,
            note=note
        )

        # Підтвердження клієнту
        client_text = (
            f"✅ *Бронювання підтверджено!*\n\n"
            f"🪑 Столик: {table_name}\n"
            f"📅 Дата: {date}\n"
            f"🕐 Час: {time}\n"
            f"👥 Гостей: {guests}\n"
            f"👤 Ім'я: {name}\n"
            f"📞 Телефон: {phone}\n"
            + (f"📝 Побажання: {note}\n" if note else "") +
            f"\n🔖 Номер бронювання: #{booking_id}"
        )
        await message.answer(client_text, parse_mode="Markdown")

        # Повідомлення адміну
        if ADMIN_ID:
            admin_text = (
                f"🔔 *Нове бронювання #{booking_id}*\n\n"
                f"🪑 {table_name} · {guests} ос.\n"
                f"📅 {date} о {time}\n"
                f"👤 {name} · {phone}\n"
                + (f"📝 {note}" if note else "")
            )
            builder = InlineKeyboardBuilder()
            builder.add(InlineKeyboardButton(
                text="✅ Підтвердити",
                callback_data=f"confirm_{booking_id}"
            ))
            builder.add(InlineKeyboardButton(
                text="❌ Скасувати",
                callback_data=f"cancel_{booking_id}"
            ))
            await bot.send_message(
                ADMIN_ID, admin_text,
                parse_mode="Markdown",
                reply_markup=builder.as_markup()
            )

    except Exception as e:
        logging.error(f"Error handling webapp data: {e}")
        await message.answer("❌ Щось пішло не так. Спробуйте ще раз.")


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(callback: types.CallbackQuery):
    booking_id = int(callback.data.split("_")[1])
    booking = await db.get_booking(booking_id)
    if booking:
        await db.update_status(booking_id, "confirmed")
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ *Підтверджено*",
            parse_mode="Markdown"
        )
        # Повідомити клієнта
        try:
            await bot.send_message(
                booking["user_id"],
                f"✅ Ваше бронювання #{booking_id} підтверджено рестораном!"
            )
        except:
            pass
    await callback.answer("Підтверджено!")


@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_booking(callback: types.CallbackQuery):
    booking_id = int(callback.data.split("_")[1])
    booking = await db.get_booking(booking_id)
    if booking:
        await db.update_status(booking_id, "cancelled")
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ *Скасовано*",
            parse_mode="Markdown"
        )
        try:
            await bot.send_message(
                booking["user_id"],
                f"❌ На жаль, ваше бронювання #{booking_id} скасовано. "
                f"Зателефонуйте нам для уточнення деталей."
            )
        except:
            pass
    await callback.answer("Скасовано!")


async def main():
    await db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
