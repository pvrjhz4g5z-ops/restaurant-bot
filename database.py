import asyncpg
import os

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
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


async def save_booking(user_id, table_name, date, time, guests, name, phone, note):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO bookings
               (user_id, table_name, date, time, guests, name, phone, note)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
               RETURNING id""",
            user_id, table_name, date, time, guests, name, phone, note
        )
        return row['id']


async def get_booking(booking_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM bookings WHERE id = $1", booking_id
        )
        return dict(row) if row else None


async def update_status(booking_id, status):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE bookings SET status = $1 WHERE id = $2",
            status, booking_id
        )


async def get_booked_slots(date, table_name):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT time FROM bookings
               WHERE date = $1 AND table_name = $2 AND status != 'cancelled'""",
            date, table_name
        )
        return [r['time'] for r in rows]


async def get_all_bookings(date=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if date:
            rows = await conn.fetch(
                "SELECT * FROM bookings WHERE date = $1 ORDER BY time", date
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM bookings ORDER BY date, time"
            )
        return [dict(r) for r in rows]
