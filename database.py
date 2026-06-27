import psycopg2
import psycopg2.extras
import os

DB_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DB_URL)


async def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
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
    conn.commit()
    cur.close()
    conn.close()


async def save_booking(user_id, table_name, date, time, guests, name, phone, note):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO bookings
           (user_id, table_name, date, time, guests, name, phone, note)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (user_id, table_name, date, time, guests, name, phone, note)
    )
    booking_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return booking_id


async def get_booking(booking_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


async def update_status(booking_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE bookings SET status = %s WHERE id = %s", (status, booking_id))
    conn.commit()
    cur.close()
    conn.close()


async def get_booked_slots(date, table_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT time FROM bookings
           WHERE date = %s AND table_name = %s AND status != 'cancelled'""",
        (date, table_name)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]


async def get_all_bookings(date=None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if date:
        cur.execute("SELECT * FROM bookings WHERE date = %s ORDER BY time", (date,))
    else:
        cur.execute("SELECT * FROM bookings ORDER BY date, time")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]
