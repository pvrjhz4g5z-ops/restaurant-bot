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
        table_name = str(data.get("tableName", "—"))[:50]
        date = str(data.get("date", "—"))[:20]
        time = str(data.get("time", "—"))[:10]
        guests = data.get("guests", 1)
        name = str(data.get("name", "—"))[:100]
        phone = str(data.get("phone", "—"))[:30]
        note = str(data.get("note", ""))[:300]

        # ── Валідація ──
        import re
        from datetime import datetime, date as date_cls

        VALID_TABLES = {f"Стіл {i}" for i in range(1, 11)} | {"VIP-стіл"} | {f"Бар {i}" for i in range(1, 6)}
        VALID_TIMES = {'12:00','12:30','13:00','13:30','14:00','14:30',
                       '18:00','18:30','19:00','19:30','20:00','20:30','21:00','21:30'}

        # Стіл має бути зі списку
        if table_name not in VALID_TABLES:
            await message.answer("❌ Невірний столик.")
            return
        # Час має бути зі списку
        if time not in VALID_TIMES:
            await message.answer("❌ Невірний час.")
            return
        # Дата у правильному форматі і не в минулому
        try:
            booking_date = datetime.strptime(date, "%Y-%m-%d").date()
            if booking_date < date_cls.today():
                await message.answer("❌ Не можна бронювати на минулу дату.")
                return
        except ValueError:
            await message.answer("❌ Невірна дата.")
            return
        # Гостей — число від 1 до 6
        try:
            guests = int(guests)
            if guests < 1 or guests > 6:
                await message.answer("❌ Невірна кількість гостей.")
                return
        except (ValueError, TypeError):
            await message.answer("❌ Невірна кількість гостей.")
            return
        # Ім'я не порожнє
        if not name.strip() or name == "—":
            await message.answer("❌ Вкажіть ім'я.")
            return
        # Телефон містить цифри
        if not re.search(r'\d{6,}', phone):
            await message.answer("❌ Невірний номер телефону.")
            return
        # Перевірка чи стіл вже зайнятий на цей час
        taken = await db.get_booked_slots(date, table_name)
        if time in taken:
            await message.answer("❌ На жаль, цей столик вже заброньований на обраний час. Оберіть інший.")
            return

        # Ліміт активних бронювань на одного користувача
        all_bookings = await db.get_all_bookings()
        active_count = sum(
            1 for b in all_bookings
            if b.get('user_id') == message.from_user.id and b.get('status') in ('pending', 'confirmed')
        )
        if active_count >= 3:
            await message.answer(
                "❌ У вас вже є 3 активні бронювання. "
                "Дочекайтесь їх завершення або скасуйте одне, щоб забронювати нове."
            )
            return

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
# ── HTTP API with rate limiting ──
import time as time_module
from collections import defaultdict

_rate_limit = defaultdict(list)
RATE_LIMIT_MAX = 30  # requests
RATE_LIMIT_WINDOW = 60  # seconds


def check_rate_limit(ip):
    now = time_module.time()
    _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit[ip].append(now)
    return True


async def api_tables(request):
    ip = request.headers.get('X-Forwarded-For', request.remote or 'unknown').split(',')[0]
    if not check_rate_limit(ip):
        return web.json_response({"booked_tables": [], "error": "rate_limited"}, status=429,
                                 headers={"Access-Control-Allow-Origin": "*"})
    date = request.rel_url.query.get('date', '')[:20]
    try:
        bookings = await db.get_all_bookings(date)
        booked_tables = list(set(b['table_name'] for b in bookings if b['status'] != 'cancelled'))
        return web.json_response({"booked_tables": booked_tables}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception:
        return web.json_response({"booked_tables": []}, headers={"Access-Control-Allow-Origin": "*"})


async def api_slots(request):
    ip = request.headers.get('X-Forwarded-For', request.remote or 'unknown').split(',')[0]
    if not check_rate_limit(ip):
        return web.json_response({"taken": [], "error": "rate_limited"}, status=429,
                                 headers={"Access-Control-Allow-Origin": "*"})
    date = request.rel_url.query.get('date', '')[:20]
    table = request.rel_url.query.get('table', '')[:50]
    try:
        taken = await db.get_booked_slots(date, table)
        return web.json_response({"taken": taken}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception:
        return web.json_response({"taken": []}, headers={"Access-Control-Allow-Origin": "*"})


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
