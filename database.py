import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "bookings.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                table_name TEXT,
                date TEXT,
                time TEXT,
                guests INTEGER,
                name TEXT,
                phone TEXT,
                note TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def save_booking(user_id, table_name, date, time, guests, name, phone, note):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO bookings
               (user_id, table_name, date, time, guests, name, phone, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, table_name, date, time, guests, name, phone, note)
        )
        await db.commit()
        return cursor.lastrowid


async def get_booking(booking_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bookings WHERE id = ?", (booking_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_status(booking_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bookings SET status = ? WHERE id = ?",
            (status, booking_id)
        )
        await db.commit()


async def get_all_bookings(date=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if date:
            async with db.execute(
                "SELECT * FROM bookings WHERE date = ? ORDER BY time",
                (date,)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM bookings ORDER BY date, time"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_booked_slots(date):
    """Повертає зайняті слоти для конкретної дати."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT table_name, time FROM bookings
               WHERE date = ? AND status != 'cancelled'""",
            (date,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]
