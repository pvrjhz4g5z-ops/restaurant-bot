import aiopg
import os
import json

_pool = None
DB_URL = os.getenv("DATABASE_URL")

DEFAULT_SLUG = "default"


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await aiopg.create_pool(DB_URL)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # ── Таблиця ресторанів (мультитенант) ──
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS restaurants (
                    id SERIAL PRIMARY KEY,
                    slug TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    admin_id BIGINT,
                    admin_key TEXT UNIQUE,
                    tables_config TEXT,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Підписка: до якої дати оплачено (новим — 14 днів пробного)
            await cur.execute("""
                ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS paid_until TEXT
            """)

            # ── Таблиця бронювань ──
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    restaurant_id INTEGER,
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

            # Якщо bookings існувала раніше без restaurant_id — додаємо колонку
            await cur.execute("""
                ALTER TABLE bookings ADD COLUMN IF NOT EXISTS restaurant_id INTEGER
            """)
            await cur.execute("""
                ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reminded BOOLEAN DEFAULT FALSE
            """)

            # ── Таблиця додаткових адмінів закладу (команда) ──
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS restaurant_admins (
                    id SERIAL PRIMARY KEY,
                    restaurant_id INTEGER NOT NULL,
                    telegram_id BIGINT NOT NULL,
                    label TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ── Ресторан за замовчуванням (щоб поточний бот не зламався) ──
            await cur.execute("SELECT id FROM restaurants WHERE slug = %s", (DEFAULT_SLUG,))
            row = await cur.fetchone()
            if not row:
                default_tables = json.dumps([
                    {"id": str(i), "name": f"Стіл {i}", "seats": 2 if i in (1,2,3,7,9) else 4}
                    for i in range(1, 10)
                ] + [
                    {"id": "10", "name": "VIP-стіл", "seats": 6}
                ] + [
                    {"id": f"b{i}", "name": f"Бар {i}", "seats": 1} for i in range(1, 6)
                ])
                admin_id = int(os.getenv("ADMIN_ID", "0"))
                admin_key = os.getenv("ADMIN_KEY", "")
                await cur.execute(
                    """INSERT INTO restaurants (slug, name, admin_id, admin_key, tables_config)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                    (DEFAULT_SLUG, "Мій ресторан", admin_id, admin_key, default_tables)
                )
                row = await cur.fetchone()

            default_id = row[0]

            # Прив'язуємо старі бронювання (без restaurant_id) до дефолтного ресторану
            await cur.execute(
                "UPDATE bookings SET restaurant_id = %s WHERE restaurant_id IS NULL",
                (default_id,)
            )

            # Таблиця кодів доступу
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS access_codes (
                    id SERIAL PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    plan TEXT NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    used_by_slug TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ── Захист від подвійних бронювань (race condition) ──
            # Унікальний індекс: не може бути двох активних бронювань
            # на той самий стіл, дату і час в одному закладі
            await cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_booking
                ON bookings (restaurant_id, date, time, table_name)
                WHERE status != 'cancelled'
            """)


# ────────────────── РЕСТОРАНИ ──────────────────

async def create_restaurant(slug, name, admin_id, admin_key, tables_config):
    """Створює новий заклад з 14-денним пробним періодом."""
    from datetime import date, timedelta
    trial_until = (date.today() + timedelta(days=14)).isoformat()
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO restaurants (slug, name, admin_id, admin_key, tables_config, paid_until)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (slug, name, admin_id, admin_key, json.dumps(tables_config), trial_until)
            )
            row = await cur.fetchone()
            return row[0]


async def get_restaurant_by_slug(slug):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, slug, name, admin_id, admin_key, tables_config, active, paid_until FROM restaurants WHERE slug = %s",
                (slug,)
            )
            row = await cur.fetchone()
            if not row:
                return None
            return _restaurant_row_to_dict(row)


async def get_restaurant_by_admin_key(key):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, slug, name, admin_id, admin_key, tables_config, active, paid_until FROM restaurants WHERE admin_key = %s",
                (key,)
            )
            row = await cur.fetchone()
            if not row:
                return None
            return _restaurant_row_to_dict(row)


async def get_restaurant_by_id(restaurant_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, slug, name, admin_id, admin_key, tables_config, active, paid_until FROM restaurants WHERE id = %s",
                (restaurant_id,)
            )
            row = await cur.fetchone()
            if not row:
                return None
            return _restaurant_row_to_dict(row)


async def list_restaurants():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, slug, name, admin_id, admin_key, tables_config, active, paid_until FROM restaurants ORDER BY id"
            )
            rows = await cur.fetchall()
            return [_restaurant_row_to_dict(r) for r in rows]


def _restaurant_row_to_dict(row):
    keys = ['id', 'slug', 'name', 'admin_id', 'admin_key', 'tables_config', 'active', 'paid_until']
    d = dict(zip(keys, row))
    try:
        d['tables_config'] = json.loads(d['tables_config']) if d['tables_config'] else []
    except (json.JSONDecodeError, TypeError):
        d['tables_config'] = []
    return d


def is_subscription_active(restaurant):
    """Чи діє підписка (пробний період або оплата)."""
    from datetime import date
    paid_until = restaurant.get('paid_until')
    if not paid_until:
        return True  # старі заклади без поля — не блокуємо
    try:
        return date.fromisoformat(str(paid_until)) >= date.today()
    except (ValueError, TypeError):
        return True


async def extend_subscription(restaurant_id, months):
    """Продовжує підписку на N місяців від сьогодні або від поточної дати оплати."""
    from datetime import date, timedelta
    r = await get_restaurant_by_id(restaurant_id)
    if not r:
        return None
    base = date.today()
    if r.get('paid_until'):
        try:
            current = date.fromisoformat(str(r['paid_until']))
            if current > base:
                base = current
        except (ValueError, TypeError):
            pass
    new_until = (base + timedelta(days=30 * months)).isoformat()
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE restaurants SET paid_until = %s WHERE id = %s",
                (new_until, restaurant_id)
            )
    return new_until


async def get_default_restaurant_id():
    r = await get_restaurant_by_slug(DEFAULT_SLUG)
    return r['id'] if r else None


# ────────────────── БРОНЮВАННЯ ──────────────────

async def save_booking(user_id, table_name, date, time, guests, name, phone, note, restaurant_id=None):
    """Зберігає бронювання. Повертає id, або None якщо стіл вже зайнятий
    на цей час (спрацював унікальний індекс — конкурентне бронювання)."""
    import psycopg2
    pool = await get_pool()
    if restaurant_id is None:
        restaurant_id = await get_default_restaurant_id()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(
                    """INSERT INTO bookings
                       (restaurant_id, user_id, table_name, date, time, guests, name, phone, note)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    (restaurant_id, user_id, table_name, date, time, guests, name, phone, note)
                )
                row = await cur.fetchone()
                return row[0]
            except psycopg2.errors.UniqueViolation:
                return None
            except psycopg2.IntegrityError:
                return None


async def get_booking(booking_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, restaurant_id, user_id, table_name, date, time, guests, name, phone, note, status FROM bookings WHERE id = %s",
                (booking_id,)
            )
            row = await cur.fetchone()
            if not row:
                return None
            keys = ['id','restaurant_id','user_id','table_name','date','time','guests','name','phone','note','status']
            return dict(zip(keys, row))


async def update_status(booking_id, status):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE bookings SET status = %s WHERE id = %s",
                (status, booking_id)
            )


async def get_booked_slots(date, table_name, restaurant_id=None):
    pool = await get_pool()
    if restaurant_id is None:
        restaurant_id = await get_default_restaurant_id()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT time FROM bookings
                   WHERE date = %s AND table_name = %s AND restaurant_id = %s AND status != 'cancelled'""",
                (date, table_name, restaurant_id)
            )
            rows = await cur.fetchall()
            return [r[0] for r in rows]


async def get_all_bookings(date=None, restaurant_id=None):
    """Повертає бронювання (за замовчуванням — тільки дефолтного ресторану, якщо restaurant_id не вказано)."""
    pool = await get_pool()
    if restaurant_id is None:
        restaurant_id = await get_default_restaurant_id()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            keys = ['id','restaurant_id','user_id','table_name','date','time','guests','name','phone','note','status','created_at']
            cols = ", ".join(keys)
            if date:
                await cur.execute(
                    f"SELECT {cols} FROM bookings WHERE restaurant_id = %s AND date = %s ORDER BY date, time",
                    (restaurant_id, date)
                )
            else:
                await cur.execute(
                    f"SELECT {cols} FROM bookings WHERE restaurant_id = %s ORDER BY date, time",
                    (restaurant_id,)
                )
            rows = await cur.fetchall()
            return [dict(zip(keys, r)) for r in rows]


# ────────────────── НАЛАШТУВАННЯ ЗАКЛАДУ ──────────────────

async def update_restaurant(restaurant_id, name=None, tables_config=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if name is not None:
                await cur.execute(
                    "UPDATE restaurants SET name = %s WHERE id = %s",
                    (name, restaurant_id)
                )
            if tables_config is not None:
                await cur.execute(
                    "UPDATE restaurants SET tables_config = %s WHERE id = %s",
                    (json.dumps(tables_config), restaurant_id)
                )


# ────────────────── КОМАНДА АДМІНІВ ──────────────────

async def list_restaurant_admins(restaurant_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, telegram_id, label FROM restaurant_admins WHERE restaurant_id = %s ORDER BY id",
                (restaurant_id,)
            )
            rows = await cur.fetchall()
            return [{"id": r[0], "telegram_id": r[1], "label": r[2]} for r in rows]


async def add_restaurant_admin(restaurant_id, telegram_id, label=""):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO restaurant_admins (restaurant_id, telegram_id, label) VALUES (%s, %s, %s) RETURNING id",
                (restaurant_id, telegram_id, label)
            )
            row = await cur.fetchone()
            return row[0]


async def remove_restaurant_admin(admin_row_id, restaurant_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM restaurant_admins WHERE id = %s AND restaurant_id = %s",
                (admin_row_id, restaurant_id)
            )


async def get_all_admin_ids(restaurant):
    """Повертає список усіх Telegram ID, яким слід надсилати сповіщення про бронювання."""
    ids = []
    if restaurant.get("admin_id"):
        ids.append(restaurant["admin_id"])
    extra = await list_restaurant_admins(restaurant["id"])
    for a in extra:
        if a["telegram_id"] not in ids:
            ids.append(a["telegram_id"])
    return ids


# ────────────────── НАГАДУВАННЯ ──────────────────

async def get_bookings_for_reminder(date):
    """Підтверджені бронювання на дату, яким ще не надсилали нагадування."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, restaurant_id, user_id, table_name, date, time, guests, name
                   FROM bookings
                   WHERE date = %s AND status = 'confirmed' AND (reminded IS NOT TRUE)""",
                (date,)
            )
            rows = await cur.fetchall()
            keys = ['id','restaurant_id','user_id','table_name','date','time','guests','name']
            return [dict(zip(keys, r)) for r in rows]


async def mark_reminded(booking_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE bookings SET reminded = TRUE WHERE id = %s",
                (booking_id,)
            )


# ────────────────── КОДИ ДОСТУПУ (оплата → підключення) ──────────────────

async def init_access_codes_table():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS access_codes (
                    id SERIAL PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    plan TEXT NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    used_by_slug TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)


async def create_access_code(code, plan):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO access_codes (code, plan) VALUES (%s, %s) RETURNING id",
                (code, plan)
            )
            row = await cur.fetchone()
            return row[0]


async def get_access_code(code):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, code, plan, used FROM access_codes WHERE code = %s",
                (code,)
            )
            row = await cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "code": row[1], "plan": row[2], "used": row[3]}


async def mark_code_used(code, slug):
    """Атомарно позначає код використаним. Повертає True якщо саме цей виклик
    його використав, False якщо код вже був використаний (конкурентний запит)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """UPDATE access_codes SET used = TRUE, used_by_slug = %s
                   WHERE code = %s AND used IS NOT TRUE
                   RETURNING id""",
                (slug, code)
            )
            row = await cur.fetchone()
            return row is not None


async def list_unused_codes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT code, plan FROM access_codes WHERE used IS NOT TRUE ORDER BY id DESC LIMIT 20"
            )
            rows = await cur.fetchall()
            return [{"code": r[0], "plan": r[1]} for r in rows]


async def set_paid_until(restaurant_id, paid_until):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE restaurants SET paid_until = %s WHERE id = %s",
                (paid_until, restaurant_id)
            )


async def refund_access_code(code):
    """Повертає код у невикористані (якщо створення закладу не вдалося)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE access_codes SET used = FALSE, used_by_slug = NULL WHERE code = %s",
                (code,)
            )
