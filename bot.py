import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import (
    InlineKeyboardButton, ReplyKeyboardMarkup,
    KeyboardButton, WebAppInfo, Message
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
import json
import database as db
from config import BOT_TOKEN, ADMIN_ID, WEBAPP_URL, ADMIN_KEY

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


ADMIN_HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Адмін · Бронювання</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f7f6f4;--card:#fff;--ink:#1c1a17;--ink2:#6f6a63;--ink3:#a39d94;
  --line:#ece9e4;--accent:#e07020;--accent-dark:#b85510;--accent-soft:#fff3e6;
  --green:#4a8c45;--green-soft:#f0f6ef;--green-line:#bcd9b8;
  --red:#b8463a;--red-soft:#fbeeed;--red-line:#e6c0bc;
  --amber:#c98a1e;--amber-soft:#fdf6e8;--amber-line:#ecd9a8;
  --r:16px;--r-sm:10px;
}
html,body{background:var(--bg);color:var(--ink);font-family:'Inter',-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto;padding:24px 18px 60px}

/* login */
#login{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.login-card{width:100%;max-width:360px;background:var(--card);border:1px solid var(--line);border-radius:22px;padding:34px 28px;text-align:center;box-shadow:0 8px 30px rgba(28,26,23,.08)}
.login-mark{width:54px;height:54px;border-radius:14px;background:var(--accent-soft);display:flex;align-items:center;justify-content:center;margin:0 auto 20px}
.login-mark svg{width:24px;height:24px;color:var(--accent)}
.login-card h1{font-family:'Fraunces',serif;font-size:24px;font-weight:500;margin-bottom:6px}
.login-card p{font-size:13px;color:var(--ink2);margin-bottom:22px}
.login-card input{width:100%;padding:14px;background:var(--bg);border:1.5px solid var(--line);border-radius:var(--r-sm);font-size:15px;font-family:'Inter';outline:none;margin-bottom:12px;text-align:center}
.login-card input:focus{border-color:var(--accent);background:#fff}
.login-card button{width:100%;padding:15px;background:var(--accent);color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:600;font-family:'Inter';cursor:pointer}
.login-err{color:var(--red);font-size:13px;margin-top:10px;min-height:16px}

/* header */
.head{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:22px}
.head h1{font-family:'Fraunces',serif;font-size:30px;font-weight:500;line-height:1}
.head .sub{font-size:13px;color:var(--ink2);margin-top:5px}
.refresh{background:var(--card);border:1px solid var(--line);border-radius:10px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--ink2)}
.refresh svg{width:17px;height:17px}
.refresh.spin svg{animation:spin .7s linear}
@keyframes spin{to{transform:rotate(360deg)}}

/* stats */
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:20px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:16px}
.stat .n{font-family:'Fraunces',serif;font-size:28px;font-weight:500;line-height:1}
.stat .l{font-size:12px;color:var(--ink2);margin-top:4px}
.stat.amber .n{color:var(--amber)}
.stat.green .n{color:var(--green)}

/* filters */
.filters{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap;align-items:center}
.filters input[type=date]{padding:10px 12px;background:var(--card);border:1px solid var(--line);border-radius:10px;font-family:'Inter';font-size:14px;outline:none;color:var(--ink)}
.chips{display:flex;gap:6px}
.chip{padding:9px 14px;background:var(--card);border:1px solid var(--line);border-radius:99px;font-size:13px;font-weight:500;color:var(--ink2);cursor:pointer;transition:all .15s}
.chip.active{background:var(--ink);color:#fff;border-color:var(--ink)}

/* booking cards */
.list{display:flex;flex-direction:column;gap:11px}
.bk{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:16px 17px;border-left:3px solid var(--ink3)}
.bk.pending{border-left-color:var(--amber)}
.bk.confirmed{border-left-color:var(--green)}
.bk.cancelled{border-left-color:var(--red);opacity:.62}
.bk-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:11px}
.bk-table{font-family:'Fraunces',serif;font-size:18px;font-weight:500}
.bk-when{font-size:13px;color:var(--ink2);margin-top:2px}
.badge{font-size:11px;font-weight:600;padding:5px 10px;border-radius:99px;white-space:nowrap;letter-spacing:.02em}
.badge.pending{background:var(--amber-soft);color:var(--amber);border:1px solid var(--amber-line)}
.badge.confirmed{background:var(--green-soft);color:var(--green);border:1px solid var(--green-line)}
.badge.cancelled{background:var(--red-soft);color:var(--red);border:1px solid var(--red-line)}
.bk-info{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13.5px;color:var(--ink);margin-bottom:4px}
.bk-info .row{display:flex;align-items:center;gap:6px}
.bk-info svg{width:14px;height:14px;color:var(--ink3)}
.bk-info a{color:var(--accent-dark);text-decoration:none;font-weight:500}
.bk-note{font-size:13px;color:var(--ink2);font-style:italic;margin-top:7px;padding-top:9px;border-top:1px solid var(--line)}
.bk-actions{display:flex;gap:8px;margin-top:13px}
.act{flex:1;padding:11px;border-radius:10px;border:none;font-family:'Inter';font-size:13.5px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;transition:all .15s}
.act svg{width:15px;height:15px}
.act-confirm{background:var(--green);color:#fff}
.act-cancel{background:var(--red-soft);color:var(--red);border:1px solid var(--red-line)}
.act:active{transform:scale(.97)}
.act:disabled{opacity:.5;cursor:default}

.empty{text-align:center;padding:60px 20px;color:var(--ink3)}
.empty svg{width:40px;height:40px;margin-bottom:14px;opacity:.5}
.empty p{font-size:14px}
.loading{text-align:center;padding:50px;color:var(--ink3);font-size:14px}
</style>
</head>
<body>

<div id="login">
  <div class="login-card">
    <div class="login-mark">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
    </div>
    <h1>Адмін-панель</h1>
    <p>Введіть ключ доступу</p>
    <input type="password" id="key-input" placeholder="Ключ доступу" onkeydown="if(event.key==='Enter')login()">
    <button onclick="login()">Увійти</button>
    <div class="login-err" id="login-err"></div>
  </div>
</div>

<div id="panel" style="display:none">
  <div class="wrap">
    <div class="head">
      <div>
        <h1>Бронювання</h1>
        <div class="sub" id="head-sub">—</div>
      </div>
      <button class="refresh" id="refresh-btn" onclick="loadBookings(true)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5"/></svg>
      </button>
    </div>

    <div class="stats">
      <div class="stat amber"><div class="n" id="st-pending">0</div><div class="l">Очікують</div></div>
      <div class="stat green"><div class="n" id="st-confirmed">0</div><div class="l">Підтверджені</div></div>
      <div class="stat"><div class="n" id="st-total">0</div><div class="l">Всього</div></div>
    </div>

    <div class="filters">
      <input type="date" id="filter-date" onchange="render()">
      <div class="chips">
        <div class="chip active" data-status="all" onclick="setFilter(this,'all')">Всі</div>
        <div class="chip" data-status="pending" onclick="setFilter(this,'pending')">Очікують</div>
        <div class="chip" data-status="confirmed" onclick="setFilter(this,'confirmed')">Підтверджені</div>
      </div>
    </div>

    <div class="list" id="list"><div class="loading">Завантаження…</div></div>
  </div>
</div>

<script>
let ADMIN_KEY = '';
let allBookings = [];
let filterStatus = 'all';

function login(){
  const k = document.getElementById('key-input').value.trim();
  if(!k){return}
  ADMIN_KEY = k;
  fetch('/api/admin/bookings?key='+encodeURIComponent(k)).then(r=>{
    if(r.status===401){document.getElementById('login-err').textContent='Невірний ключ';return null}
    return r.json();
  }).then(d=>{
    if(!d)return;
    try{localStorage.setItem('admin_key',k)}catch(e){}
    document.getElementById('login').style.display='none';
    document.getElementById('panel').style.display='block';
    allBookings = d.bookings||[];
    render();
  }).catch(()=>{document.getElementById('login-err').textContent='Помилка з\\'єднання'});
}

function loadBookings(spin){
  if(spin){const b=document.getElementById('refresh-btn');b.classList.add('spin');setTimeout(()=>b.classList.remove('spin'),700)}
  fetch('/api/admin/bookings?key='+encodeURIComponent(ADMIN_KEY)).then(r=>r.json()).then(d=>{
    allBookings=d.bookings||[];render();
  }).catch(()=>{});
}

function setFilter(el,status){
  document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  filterStatus=status;render();
}

function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}

function render(){
  const dateF = document.getElementById('filter-date').value;
  let list = allBookings.slice();

  // stats (на всіх, не на фільтрованих)
  const pending = allBookings.filter(b=>b.status==='pending').length;
  const confirmed = allBookings.filter(b=>b.status==='confirmed').length;
  document.getElementById('st-pending').textContent=pending;
  document.getElementById('st-confirmed').textContent=confirmed;
  document.getElementById('st-total').textContent=allBookings.filter(b=>b.status!=='cancelled').length;
  document.getElementById('head-sub').textContent=pending>0?(pending+' очікують підтвердження'):'Все опрацьовано';

  if(dateF) list=list.filter(b=>b.date===dateF);
  if(filterStatus!=='all') list=list.filter(b=>b.status===filterStatus);

  // сорт: pending перші, далі за датою+часом
  const order={pending:0,confirmed:1,cancelled:2};
  list.sort((a,b)=>{
    if(order[a.status]!==order[b.status])return order[a.status]-order[b.status];
    return (a.date+a.time).localeCompare(b.date+b.time);
  });

  const wrap=document.getElementById('list');
  if(list.length===0){
    wrap.innerHTML='<div class="empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg><p>Бронювань немає</p></div>';
    return;
  }

  const stLabel={pending:'Очікує',confirmed:'Підтверджено',cancelled:'Скасовано'};
  wrap.innerHTML=list.map(b=>{
    const d=new Date(b.date+'T00:00:00');
    const dateStr=isNaN(d)?b.date:d.toLocaleDateString('uk-UA',{day:'numeric',month:'long'});
    const phoneDigits=String(b.phone||'').replace(/[^0-9+]/g,'');
    return `<div class="bk ${b.status}">
      <div class="bk-top">
        <div>
          <div class="bk-table">${esc(b.table_name)}</div>
          <div class="bk-when">${dateStr} · ${esc(b.time)}</div>
        </div>
        <span class="badge ${b.status}">${stLabel[b.status]||b.status}</span>
      </div>
      <div class="bk-info">
        <span class="row"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>${esc(b.name)}</span>
        <span class="row"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.6A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/></svg><a href="tel:${phoneDigits}">${esc(b.phone)}</a></span>
        <span class="row"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/></svg>${esc(b.guests)} гост.</span>
      </div>
      ${b.note?`<div class="bk-note">«${esc(b.note)}»</div>`:''}
      ${b.status==='pending'?`<div class="bk-actions">
        <button class="act act-confirm" onclick="doAction(${b.id},'confirm',this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>Підтвердити</button>
        <button class="act act-cancel" onclick="doAction(${b.id},'cancel',this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>Скасувати</button>
      </div>`:''}
      ${b.status==='confirmed'?`<div class="bk-actions">
        <button class="act act-cancel" onclick="doAction(${b.id},'cancel',this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>Скасувати</button>
      </div>`:''}
    </div>`;
  }).join('');
}

function doAction(id,action,btn){
  const card=btn.closest('.bk');
  card.querySelectorAll('.act').forEach(b=>b.disabled=true);
  fetch('/api/admin/action?key='+encodeURIComponent(ADMIN_KEY),{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:id,action:action})
  }).then(r=>r.json()).then(d=>{
    if(d.ok){
      const b=allBookings.find(x=>x.id===id);
      if(b)b.status=d.status;
      render();
    }else{card.querySelectorAll('.act').forEach(b=>b.disabled=false)}
  }).catch(()=>{card.querySelectorAll('.act').forEach(b=>b.disabled=false)});
}

// автологін якщо ключ збережено
try{
  const saved=localStorage.getItem('admin_key');
  if(saved){document.getElementById('key-input').value=saved;login()}
}catch(e){}

// автооновлення кожні 30с
setInterval(()=>{if(ADMIN_KEY)loadBookings(false)},30000);
</script>
</body>
</html>"""




@dp.message(CommandStart())
async def start(message: Message, command: CommandObject):
    await db.init_db()

    slug = (command.args or "").strip() or db.DEFAULT_SLUG
    restaurant = await db.get_restaurant_by_slug(slug)
    if not restaurant or not restaurant.get("active", True):
        restaurant = await db.get_restaurant_by_slug(db.DEFAULT_SLUG)
        slug = db.DEFAULT_SLUG

    webapp_url = f"{WEBAPP_URL}?r={slug}"
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(
            text="🪑 Забронювати столик",
            web_app=WebAppInfo(url=webapp_url)
        )]],
        resize_keyboard=True
    )
    restaurant_name = restaurant["name"] if restaurant else "нашому ресторані"
    await message.answer(
        f"👋 Вітаємо в {restaurant_name}!\n\n"
        "Натисніть кнопку нижче, щоб обрати столик і зробити бронювання.",
        reply_markup=keyboard
    )


@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        slug = str(data.get("restaurantSlug", "") or db.DEFAULT_SLUG)[:60]
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

        restaurant = await db.get_restaurant_by_slug(slug)
        if not restaurant or not restaurant.get("active", True):
            await message.answer("❌ Заклад не знайдено. Спробуйте ще раз через /start.")
            return
        restaurant_id = restaurant["id"]

        VALID_TABLES = {t["name"] for t in restaurant.get("tables_config", [])}
        VALID_TIMES = {'12:00','12:30','13:00','13:30','14:00','14:30',
                       '18:00','18:30','19:00','19:30','20:00','20:30','21:00','21:30'}

        # Стіл має бути зі списку цього закладу
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
        digit_count = len(re.findall(r'\d', phone))
        if digit_count < 7:
            await message.answer("❌ Невірний номер телефону.")
            return
        # Перевірка чи стіл вже зайнятий на цей час (в межах цього закладу)
        taken = await db.get_booked_slots(date, table_name, restaurant_id=restaurant_id)
        if time in taken:
            await message.answer("❌ На жаль, цей столик вже заброньований на обраний час. Оберіть інший.")
            return

        # Ліміт активних бронювань на одного користувача (в межах цього закладу)
        all_bookings = await db.get_all_bookings(restaurant_id=restaurant_id)
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
            note=note,
            restaurant_id=restaurant_id
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

        restaurant_admin_id = restaurant.get("admin_id") or ADMIN_ID
        if restaurant_admin_id:
            admin_text = (
                f"🔔 *Нове бронювання #{booking_id}*\n\n"
                f"🏠 {restaurant['name']}\n"
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
                restaurant_admin_id, admin_text,
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


async def api_restaurant(request):
    """Повертає інформацію про заклад і його столи для WebApp."""
    slug = request.rel_url.query.get('r', '')[:60] or db.DEFAULT_SLUG
    try:
        restaurant = await db.get_restaurant_by_slug(slug)
        if not restaurant or not restaurant.get("active", True):
            restaurant = await db.get_restaurant_by_slug(db.DEFAULT_SLUG)
        if not restaurant:
            return web.json_response({"error": "not_found"}, status=404,
                                     headers={"Access-Control-Allow-Origin": "*"})
        return web.json_response({
            "slug": restaurant["slug"],
            "name": restaurant["name"],
            "tables": restaurant.get("tables_config", [])
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception:
        return web.json_response({"error": "failed"}, status=500,
                                 headers={"Access-Control-Allow-Origin": "*"})


async def api_tables(request):
    ip = request.headers.get('X-Forwarded-For', request.remote or 'unknown').split(',')[0]
    if not check_rate_limit(ip):
        return web.json_response({"booked_tables": [], "error": "rate_limited"}, status=429,
                                 headers={"Access-Control-Allow-Origin": "*"})
    date = request.rel_url.query.get('date', '')[:20]
    slug = request.rel_url.query.get('r', '')[:60] or db.DEFAULT_SLUG
    try:
        restaurant = await db.get_restaurant_by_slug(slug)
        restaurant_id = restaurant["id"] if restaurant else None
        bookings = await db.get_all_bookings(date, restaurant_id=restaurant_id)
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
    slug = request.rel_url.query.get('r', '')[:60] or db.DEFAULT_SLUG
    try:
        restaurant = await db.get_restaurant_by_slug(slug)
        restaurant_id = restaurant["id"] if restaurant else None
        taken = await db.get_booked_slots(date, table, restaurant_id=restaurant_id)
        return web.json_response({"taken": taken}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception:
        return web.json_response({"taken": []}, headers={"Access-Control-Allow-Origin": "*"})


# ────────────────── ADMIN PANEL ──────────────────

async def _get_restaurant_from_key(request):
    """Знаходить заклад за секретним ключем адміна (з query або заголовка)."""
    key = request.rel_url.query.get('key', '') or request.headers.get('X-Admin-Key', '')
    if not key:
        return None
    restaurant = await db.get_restaurant_by_admin_key(key)
    if restaurant and restaurant.get("active", True):
        return restaurant
    return None


async def admin_page(request):
    """Віддає HTML сторінку адмін-панелі (ключ перевіряється на фронті через API)."""
    return web.Response(text=ADMIN_HTML, content_type='text/html')


async def admin_bookings(request):
    """API: список бронювань для закладу, прив'язаного до ключа адміна."""
    restaurant = await _get_restaurant_from_key(request)
    if not restaurant:
        return web.json_response({"error": "unauthorized"}, status=401)
    date = request.rel_url.query.get('date', '')[:20] or None
    try:
        bookings = await db.get_all_bookings(date, restaurant_id=restaurant["id"])
        def to_str(b):
            return {
                "id": b.get("id"),
                "table_name": b.get("table_name"),
                "date": b.get("date"),
                "time": b.get("time"),
                "guests": b.get("guests"),
                "name": b.get("name"),
                "phone": b.get("phone"),
                "note": b.get("note") or "",
                "status": b.get("status") or "pending",
            }
        result = [to_str(b) for b in bookings]
        return web.json_response({"bookings": result, "restaurant_name": restaurant["name"]})
    except Exception:
        return web.json_response({"bookings": []})


async def admin_action(request):
    """API: змінити статус бронювання (confirm / cancel) — тільки для свого закладу."""
    restaurant = await _get_restaurant_from_key(request)
    if not restaurant:
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        data = await request.json()
        booking_id = int(data.get("id"))
        action = data.get("action", "")
        status_map = {"confirm": "confirmed", "cancel": "cancelled"}
        if action not in status_map:
            return web.json_response({"error": "bad_action"}, status=400)

        # Перевірка що бронювання належить саме цьому закладу
        existing = await db.get_booking(booking_id)
        if not existing or existing.get("restaurant_id") != restaurant["id"]:
            return web.json_response({"error": "not_found"}, status=404)

        new_status = status_map[action]
        await db.update_status(booking_id, new_status)

        # Повідомити клієнта
        try:
            b = await db.get_booking(booking_id)
            if b and b.get("user_id"):
                if new_status == "confirmed":
                    msg = (f"✅ Ваше бронювання підтверджено!\n\n"
                           f"🪑 {b['table_name']}\n📅 {b['date']} о {b['time']}\n"
                           f"👥 {b['guests']} гост.\n\nЧекаємо на вас!")
                else:
                    msg = (f"❌ На жаль, бронювання скасовано.\n\n"
                           f"🪑 {b['table_name']}\n📅 {b['date']} о {b['time']}\n\n"
                           f"Зв'яжіться з нами, щоб обрати інший час.")
                await bot.send_message(b["user_id"], msg)
        except Exception:
            pass

        return web.json_response({"ok": True, "status": new_status})
    except Exception:
        return web.json_response({"error": "failed"}, status=500)


async def main():
    await db.init_db()
    await bot.delete_webhook(drop_pending_updates=True)

    # Start HTTP server
    app = web.Application()
    app.router.add_get('/api/restaurant', api_restaurant)
    app.router.add_get('/api/tables', api_tables)
    app.router.add_get('/api/slots', api_slots)
    app.router.add_get('/admin', admin_page)
    app.router.add_get('/api/admin/bookings', admin_bookings)
    app.router.add_post('/api/admin/action', admin_action)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logging.info("API server started on port 8080")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
