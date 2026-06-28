import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton, ReplyKeyboardMarkup,
    KeyboardButton, WebAppInfo, Message
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
import json
import database as db
from config import BOT_TOKEN, ADMIN_ID, WEBAPP_URL

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await db.init_db()
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(
            text="🪑 Забронювати столик",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]],
        resize_keyboard=True
    )
    await message.answer(
        "👋 Вітаємо в нашому ресторані!\n\n"
        "Натисніть кнопку нижче, щоб обрати столик і зробити бронювання.",
        reply_markup=keyboard
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
                f"❌ На жаль, ваше бронювання #{booking_id} скасовано."
            )
        except:
            pass
    await callback.answer("Скасовано!")


# ── HTTP API ──
async def api_tables(request):
    date = request.rel_url.query.get('date', '')
    try:
        bookings = await db.get_all_bookings(date)
        booked_tables = list(set(b['table_name'] for b in bookings if b['status'] != 'cancelled'))
        return web.json_response({"booked_tables": booked_tables}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"booked_tables": [], "error": str(e)})


async def api_slots(request):
    date = request.rel_url.query.get('date', '')
    table = request.rel_url.query.get('table', '')
    try:
        taken = await db.get_booked_slots(date, table)
        return web.json_response({"taken": taken}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"taken": [], "error": str(e)})


async def main():
    await db.init_db()
    await bot.delete_webhook(drop_pending_updates=True)

    # Start HTTP server
    app = web.Application()
    app.router.add_get('/api/tables', api_tables)
    app.router.add_get('/api/slots', api_slots)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logging.info("API server started on port 8080")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
