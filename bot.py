import aiopg
import os
import json

_pool = None
DB_URL = os.getenv("DATABASE_URL")

DEFAULT_SLUG = "default"

DEFAULT_TIME_SLOTS = [
    '12:00','12:30','13:00','13:30','14:00','14:30',
    '18:00','18:30','19:00','19:30','20:00','20:30','21:00','21:30'
]


async def get_pool():
    global _pool
    if _pool is None:
        if not DB_URL:
            raise RuntimeError(
                "DATABASE_URL не заданий. У Railway додайте змінну оточення "
                "DATABASE_URL з посиланням на PostgreSQL."
            )
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

            # Слоти часу закладу (JSON-масив "HH:MM"). NULL = дефолтні.
            await cur.execute("""
                ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS time_slots TEXT
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

            # fix8: тримаємо admin_key/admin_id дефолтного закладу в синхроні з env,
            # щоб зміна ADMIN_KEY у Railway не залишала старий ключ у базі
            env_admin_id = int(os.getenv("ADMIN_ID", "0"))
            env_admin_key = os.getenv("ADMIN_KEY", "")
            if env_admin_key:
                await cur.execute(
                    "UPDATE restaurants SET admin_key = %s, admin_id = %s WHERE slug = %s",
                    (env_admin_key, env_admin_id, DEFAULT_SLUG)
                )

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

            # ── Тимчасові холди столів (поки клієнт заповнює форму) ──
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS table_holds (
                    id SERIAL PRIMARY KEY,
                    restaurant_id INTEGER NOT NULL,
                    table_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    user_id BIGINT NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            # Один активний хол на комбінацію стіл+дата+час
            await cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_hold
                ON table_holds (restaurant_id, date, time, table_name)
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
                "SELECT id, slug, name, admin_id, admin_key, tables_config, active, paid_until, time_slots FROM restaurants WHERE slug = %s",
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
                "SELECT id, slug, name, admin_id, admin_key, tables_config, active, paid_until, time_slots FROM restaurants WHERE admin_key = %s",
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
                "SELECT id, slug, name, admin_id, admin_key, tables_config, active, paid_until, time_slots FROM restaurants WHERE id = %s",
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
                "SELECT id, slug, name, admin_id, admin_key, tables_config, active, paid_until, time_slots FROM restaurants ORDER BY id"
            )
            rows = await cur.fetchall()
            return [_restaurant_row_to_dict(r) for r in rows]


def _restaurant_row_to_dict(row):
    keys = ['id', 'slug', 'name', 'admin_id', 'admin_key', 'tables_config', 'active', 'paid_until', 'time_slots']
    d = dict(zip(keys, row))
    try:
        d['tables_config'] = json.loads(d['tables_config']) if d['tables_config'] else []
    except (json.JSONDecodeError, TypeError):
        d['tables_config'] = []
    try:
        slots = json.loads(d['time_slots']) if d.get('time_slots') else None
        d['time_slots'] = slots if slots else DEFAULT_TIME_SLOTS
    except (json.JSONDecodeError, TypeError):
        d['time_slots'] = DEFAULT_TIME_SLOTS
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

async def count_active_bookings_for_user(user_id, restaurant_id):
    """Швидкий підрахунок активних бронювань юзера (без вивантаження всіх)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT COUNT(*) FROM bookings
                   WHERE user_id = %s AND restaurant_id = %s
                   AND status IN ('pending', 'confirmed')""",
                (user_id, restaurant_id)
            )
            row = await cur.fetchone()
            return row[0] if row else 0

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


def _booking_is_expired(date_str, time_str, hours_after=2):
    """Бронь вважається завершеною через hours_after годин після часу візиту."""
    from datetime import datetime, timedelta
    try:
        bt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return False
    return datetime.now() > bt + timedelta(hours=hours_after)


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
            # Прострочені броні (час візиту + 2 год минув) не блокують стіл
            return [r[0] for r in rows if not _booking_is_expired(date, r[0])]


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

async def update_restaurant(restaurant_id, name=None, tables_config=None, time_slots=None):
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
            if time_slots is not None:
                await cur.execute(
                    "UPDATE restaurants SET time_slots = %s WHERE id = %s",
                    (json.dumps(time_slots), restaurant_id)
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


async def get_active_booking_tables(restaurant_id):
    """Повертає назви столів, на які є активні (не скасовані) бронювання від сьогодні."""
    from datetime import date as _date
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT DISTINCT table_name FROM bookings
                   WHERE restaurant_id = %s AND status != 'cancelled'
                   AND date >= %s""",
                (restaurant_id, _date.today().isoformat())
            )
            rows = await cur.fetchall()
            return [r[0] for r in rows]


# ────────────────── ТИМЧАСОВІ ХОЛДИ СТОЛІВ ──────────────────

HOLD_MINUTES = 3

async def create_hold(restaurant_id, table_name, date, time, user_id):
    """Резервує стіл за користувачем на HOLD_MINUTES хвилин (атомарно).
    Повертає True якщо вдалось, False якщо стіл вже тримає ХТОСЬ ІНШИЙ або вже заброньований."""
    from datetime import datetime, timedelta
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Чи вже є активне бронювання на цей слот?
            await cur.execute(
                """SELECT 1 FROM bookings
                   WHERE restaurant_id=%s AND date=%s AND time=%s AND table_name=%s
                   AND status != 'cancelled' LIMIT 1""",
                (restaurant_id, date, time, table_name)
            )
            if await cur.fetchone():
                return False

            expires = datetime.now() + timedelta(minutes=HOLD_MINUTES)
            # Атомарно: вставляємо хол АБО перезаписуємо, якщо існуючий протермінований
            # чи належить цьому ж юзеру. Якщо активний хол іншого юзера — ON CONFLICT
            # оновить рядок лише коли виконується WHERE, інакше нічого не зміниться.
            await cur.execute(
                """INSERT INTO table_holds
                       (restaurant_id, table_name, date, time, user_id, expires_at)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (restaurant_id, date, time, table_name)
                   DO UPDATE SET user_id = EXCLUDED.user_id, expires_at = EXCLUDED.expires_at
                   WHERE table_holds.expires_at < CURRENT_TIMESTAMP
                      OR table_holds.user_id = EXCLUDED.user_id
                   RETURNING user_id""",
                (restaurant_id, table_name, date, time, user_id, expires)
            )
            row = await cur.fetchone()
            # RETURNING поверне рядок лише якщо INSERT або дозволений UPDATE відбувся
            return bool(row and row[0] == user_id)


async def release_hold(restaurant_id, table_name, date, time, user_id):
    """Знімає хол (наприклад після успішного бронювання або скасування вибору)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """DELETE FROM table_holds
                   WHERE restaurant_id=%s AND date=%s AND time=%s AND table_name=%s AND user_id=%s""",
                (restaurant_id, date, time, table_name, user_id)
            )


async def get_held_tables(restaurant_id, date, time, exclude_user_id=None):
    """Повертає назви столів, які зараз тримає ХТОСЬ ІНШИЙ (активні, не протерміновані холди)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if exclude_user_id is not None:
                await cur.execute(
                    """SELECT table_name FROM table_holds
                       WHERE restaurant_id=%s AND date=%s AND time=%s AND user_id != %s
                       AND expires_at >= CURRENT_TIMESTAMP""",
                    (restaurant_id, date, time, exclude_user_id)
                )
            else:
                await cur.execute(
                    """SELECT table_name FROM table_holds
                       WHERE restaurant_id=%s AND date=%s AND time=%s
                       AND expires_at >= CURRENT_TIMESTAMP""",
                    (restaurant_id, date, time)
                )
            rows = await cur.fetchall()
            return [r[0] for r in rows]


async def cleanup_expired_holds():
    """Видаляє протерміновані холди. Викликається фоновою задачею."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM table_holds WHERE expires_at < CURRENT_TIMESTAMP")


# ────────────────── АТОМАРНА РЕЄСТРАЦІЯ (код + заклад в одній транзакції) ──────────────────

async def register_restaurant_with_code(slug, name, admin_id, admin_key, tables_config, access_code, plan):
    """Атомарно: забирає код доступу, створює заклад, ставить оплату.
    Все в ОДНІЙ транзакції — при будь-якому збої відкочується повністю.
    Повертає (restaurant_id, paid_until) або кидає ValueError з причиною."""
    from datetime import date, timedelta
    days = 365 if plan == "year" else 30
    trial_until = (date.today() + timedelta(days=days)).isoformat()
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("BEGIN")
            try:
                # 1. Забираємо код (тільки якщо ще не використаний)
                await cur.execute(
                    """UPDATE access_codes SET used = TRUE, used_by_slug = %s
                       WHERE code = %s AND used IS NOT TRUE RETURNING id""",
                    (slug, access_code)
                )
                if not await cur.fetchone():
                    raise ValueError("code_used")

                # 2. Перевіряємо, що slug вільний
                await cur.execute("SELECT 1 FROM restaurants WHERE slug = %s", (slug,))
                if await cur.fetchone():
                    raise ValueError("slug_taken")

                # 3. Створюємо заклад одразу з оплаченим періодом
                await cur.execute(
                    """INSERT INTO restaurants
                           (slug, name, admin_id, admin_key, tables_config, paid_until)
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                    (slug, name, admin_id, admin_key, json.dumps(tables_config), trial_until)
                )
                restaurant_id = (await cur.fetchone())[0]

                await cur.execute("COMMIT")
                return restaurant_id, trial_until
            except Exception:
                try:
                    await cur.execute("ROLLBACK")
                except Exception:
                    pass
                raise
