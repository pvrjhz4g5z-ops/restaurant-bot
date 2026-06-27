import aiopg
import os

_pool = None
DB_URL = os.getenv("DATABASE_URL")


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await aiopg.create_pool(DB_URL)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
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
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO bookings
                   (user_id, table_name, date, time, guests, name, phone, note)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (user_id, table_name, date, time, guests, name, phone, note)
            )
            row = await cur.fetchone()
            return row[0]


async def get_booking(booking_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, user_id, table_name, date, time, guests, name, phone, note, status FROM bookings WHERE id = %s",
                (booking_id,)
            )
            row = await cur.fetchone()
            if not row:
                return None
            keys = ['id','user_id','table_name','date','time','guests','name','phone','note','status']
            return dict(zip(keys, row))


async def update_status(booking_id, status):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE bookings SET status = %s WHERE id = %s",
                (status, booking_id)
            )


async def get_booked_slots(date, table_name):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT time FROM bookings
                   WHERE date = %s AND table_name = %s AND status != 'cancelled'""",
                (date, table_name)
            )
            rows = await cur.fetchall()
            return [r[0] for r in rows]
