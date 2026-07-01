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


# ────────────────── РЕЄСТРАЦІЯ НОВОГО ЗАКЛАДУ ──────────────────

import re as _re
import secrets

RESERVED_SLUGS = {"default", "admin", "api", "register", "www", "app", "bot", "static"}

_bot_username = None


async def get_bot_username():
    global _bot_username
    if _bot_username is None:
        me = await bot.get_me()
        _bot_username = me.username
    return _bot_username


def _slugify(text):
    text = text.lower().strip()
    text = _re.sub(r'[^a-z0-9а-яіїєґ\s_-]', '', text)
    text = _re.sub(r'[\s_]+', '_', text)
    return text[:40]


async def register_page(request):
    return web.Response(text=REGISTER_HTML, content_type='text/html')


async def api_check_slug(request):
    slug = request.rel_url.query.get('slug', '')[:60]
    slug = _slugify(slug)
    valid = bool(_re.match(r'^[a-z0-9а-яіїєґ_-]{3,40}$', slug)) and slug not in RESERVED_SLUGS
    available = valid
    if valid:
        existing = await db.get_restaurant_by_slug(slug)
        available = existing is None
    return web.json_response({"slug": slug, "valid": valid, "available": available})


async def api_register(request):
    ip = request.headers.get('X-Forwarded-For', request.remote or 'unknown').split(',')[0]
    if not check_rate_limit(ip):
        return web.json_response({"error": "rate_limited"}, status=429)
    try:
        data = await request.json()
        name = str(data.get("name", "")).strip()[:80]
        slug = _slugify(str(data.get("slug", "")))
        admin_id_raw = str(data.get("adminId", "")).strip()
        tables = data.get("tables", [])

        if not name or len(name) < 2:
            return web.json_response({"error": "Вкажіть назву закладу (мінімум 2 символи)."}, status=400)
        if not _re.match(r'^[a-z0-9а-яіїєґ_-]{3,40}$', slug) or slug in RESERVED_SLUGS:
            return web.json_response({"error": "Невірне посилання. Використайте 3-40 символів: літери, цифри, дефіс."}, status=400)
        existing = await db.get_restaurant_by_slug(slug)
        if existing:
            return web.json_response({"error": "Це посилання вже зайняте. Оберіть інше."}, status=400)
        try:
            admin_id = int(admin_id_raw)
            if admin_id <= 0:
                raise ValueError()
        except ValueError:
            return web.json_response({"error": "Невірний Telegram ID власника."}, status=400)

        if not isinstance(tables, list) or len(tables) == 0:
            return web.json_response({"error": "Додайте хоча б один стіл."}, status=400)
        if len(tables) > 60:
            return web.json_response({"error": "Забагато столів (максимум 60)."}, status=400)

        clean_tables = []
        for i, t in enumerate(tables):
            tname = str(t.get("name", "")).strip()[:40]
            try:
                seats = int(t.get("seats", 0))
            except (ValueError, TypeError):
                seats = 0
            if not tname or seats < 1 or seats > 30:
                return web.json_response({"error": f"Перевірте стіл №{i+1}: назва і кількість місць (1-30)."}, status=400)
            clean_tables.append({"id": str(i + 1), "name": tname, "seats": seats})

        admin_key = secrets.token_urlsafe(16)
        restaurant_id = await db.create_restaurant(slug, name, admin_id, admin_key, clean_tables)

        username = await get_bot_username()
        bot_link = f"https://t.me/{username}?start={slug}"
        # адмін-панель хоститься на цьому ж боті (Railway домен)
        base_api = request.url.scheme + "://" + request.url.host
        if request.url.port and request.url.port not in (80, 443):
            base_api += f":{request.url.port}"
        admin_url = f"{base_api}/admin?key={admin_key}"

        return web.json_response({
            "ok": True,
            "restaurant_id": restaurant_id,
            "slug": slug,
            "bot_link": bot_link,
            "admin_url": admin_url,
            "admin_key": admin_key
        })
    except Exception as e:
        logging.error(f"Register error: {e}")
        return web.json_response({"error": "Щось пішло не так. Спробуйте ще раз."}, status=500)


async def landing_page(request):
    return web.Response(text=LANDING_HTML, content_type='text/html')


LANDING_HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stolyk — бронювання столиків для вашого закладу</title>
<meta name="description" content="Онлайн-бронювання столиків через Telegram. Клієнти бронюють за хвилину, ви керуєте всім із зручної панелі.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#ffffff;--bg2:#f7f6f4;--ink:#1c1a17;--ink2:#6f6a63;--ink3:#a39d94;
  --line:#ece9e4;--accent:#e07020;--accent-dark:#b85510;--accent-soft:#fff3e6;
  --green:#4a8c45;--green-soft:#f0f6ef;--green-line:#bcd9b8;
  --r:20px;--r-sm:12px;
}
html{scroll-behavior:smooth}
html,body{background:var(--bg);color:var(--ink);font-family:'Inter',-apple-system,sans-serif;-webkit-font-smoothing:antialiased;overflow-x:hidden}
.wrap{max-width:1040px;margin:0 auto;padding:0 24px}
a{color:inherit;text-decoration:none}
img,svg{display:block}

/* NAV */
nav{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.88);backdrop-filter:saturate(180%) blur(14px);border-bottom:1px solid var(--line)}
.nav-inner{max-width:1040px;margin:0 auto;padding:16px 24px;display:flex;align-items:center;justify-content:space-between}
.logo{display:flex;align-items:center;gap:10px;font-family:'Fraunces',serif;font-size:19px;font-weight:600}
.logo-mark{width:32px;height:32px;border-radius:9px;background:linear-gradient(160deg,#e07020 0%,#b85510 100%);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.logo-mark svg{width:17px;height:17px;color:#fff}
.footer-mark{width:22px;height:22px;border-radius:6px;background:linear-gradient(160deg,#e07020 0%,#b85510 100%);display:inline-flex;align-items:center;justify-content:center;vertical-align:-6px;margin-right:6px}
.footer-mark svg{width:12px;height:12px;color:#fff}
.nav-cta{padding:10px 20px;background:var(--ink);color:#fff;border-radius:10px;font-size:13.5px;font-weight:600}
.nav-cta:active{opacity:.85}

/* HERO */
.hero{padding:64px 0 40px;text-align:center}
.hero .eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-dark);background:var(--accent-soft);padding:8px 16px;border-radius:99px;font-weight:600;margin-bottom:24px}
.hero h1{font-family:'Fraunces',serif;font-size:clamp(34px,6vw,58px);font-weight:400;line-height:1.06;letter-spacing:-.01em;margin-bottom:20px}
.hero h1 em{font-style:italic;color:var(--accent)}
.hero p{font-size:16.5px;color:var(--ink2);max-width:520px;margin:0 auto 34px;line-height:1.6}
.hero-actions{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:56px}
.btn-primary{padding:16px 30px;background:var(--accent);color:#fff;border-radius:13px;font-size:15px;font-weight:600}
.btn-primary:active{transform:scale(.98)}
.btn-ghost{padding:16px 30px;background:var(--bg2);color:var(--ink);border-radius:13px;font-size:15px;font-weight:600;border:1px solid var(--line)}

/* PHONE MOCK */
.mock-wrap{display:flex;justify-content:center;margin-bottom:20px}
.mock{width:100%;max-width:300px;aspect-ratio:340/560;background:var(--ink);border-radius:32px;padding:10px;box-shadow:0 30px 70px rgba(28,26,23,.22)}
.mock-screen{width:100%;height:100%;background:#fff;border-radius:24px;overflow:hidden;padding:18px 16px;display:flex;flex-direction:column;gap:10px}
.mock-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.mock-tbl{aspect-ratio:1;border-radius:11px;background:var(--green-soft);border:1.3px solid var(--green-line)}
.mock-tbl.busy{background:#fbeeed;border-color:#e6c0bc}
.mock-bar{height:34px;border-radius:9px;background:var(--bg2);border:1px solid var(--line);margin-bottom:2px}
.mock-btn{margin-top:auto;height:40px;border-radius:10px;background:var(--accent)}

/* STATS STRIP */
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border-radius:var(--r);overflow:hidden;margin-bottom:88px;border:1px solid var(--line)}
.stat{background:#fff;padding:26px 20px;text-align:center}
.stat .n{font-family:'Fraunces',serif;font-size:30px;font-weight:500;color:var(--accent-dark)}
.stat .l{font-size:12.5px;color:var(--ink2);margin-top:4px}

/* SECTION */
.section{padding:70px 0}
.section-head{text-align:center;max-width:560px;margin:0 auto 48px}
.section-head .eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:12px}
.section-head h2{font-family:'Fraunces',serif;font-size:clamp(26px,4vw,36px);font-weight:400;line-height:1.15}
.section-head p{font-size:15px;color:var(--ink2);margin-top:12px;line-height:1.6}

/* HOW IT WORKS */
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.step{position:relative;padding:28px 22px}
.step .num{font-family:'Fraunces',serif;font-size:15px;color:var(--accent);font-weight:500;margin-bottom:14px}
.step h3{font-size:16px;font-weight:600;margin-bottom:8px}
.step p{font-size:13.5px;color:var(--ink2);line-height:1.55}

/* FEATURES */
.features{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.feature{background:var(--bg2);border-radius:var(--r);padding:26px 22px;border:1px solid var(--line)}
.feature .ic{width:40px;height:40px;border-radius:11px;background:var(--accent-soft);display:flex;align-items:center;justify-content:center;margin-bottom:16px}
.feature .ic svg{width:19px;height:19px;color:var(--accent-dark)}
.feature h3{font-size:15px;font-weight:600;margin-bottom:6px}
.feature p{font-size:13px;color:var(--ink2);line-height:1.55}

/* CTA BAND */
.cta-band{background:var(--ink);border-radius:28px;padding:56px 40px;text-align:center;position:relative;overflow:hidden;margin-bottom:70px}
.cta-band::after{content:'';position:absolute;top:-30%;right:-15%;width:60%;height:70%;background:radial-gradient(circle,rgba(224,112,32,.35) 0%,transparent 70%)}
.cta-band h2{position:relative;font-family:'Fraunces',serif;font-size:clamp(24px,4vw,34px);font-weight:400;color:#fff;margin-bottom:14px}
.cta-band p{position:relative;color:rgba(255,255,255,.6);font-size:14.5px;margin-bottom:26px}
.cta-band .btn-primary{position:relative}

footer{border-top:1px solid var(--line);padding:28px 0;text-align:center;font-size:12.5px;color:var(--ink3)}

@media (max-width:720px){
  .steps,.features{grid-template-columns:1fr}
  .stats{grid-template-columns:1fr}
  .stat{border-bottom:1px solid var(--line)}
}
</style>
</head>
<body>

<nav>
  <div class="nav-inner">
    <div class="logo">
      <div class="logo-mark">
        <svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="5"/><circle cx="12" cy="3" r="1.7"/><circle cx="21" cy="12" r="1.7"/><circle cx="12" cy="21" r="1.7"/><circle cx="3" cy="12" r="1.7"/></svg>
      </div>
      Stolyk
    </div>
    <a href="/register" class="nav-cta">Підключити заклад</a>
  </div>
</nav>

<div class="wrap">
  <section class="hero">
    <div class="eyebrow"><svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13"><circle cx="12" cy="12" r="5"/><circle cx="12" cy="3" r="1.7"/><circle cx="21" cy="12" r="1.7"/><circle cx="12" cy="21" r="1.7"/><circle cx="3" cy="12" r="1.7"/></svg> Бронювання столиків</div>
    <h1>Столик за <em>хвилину</em>,<br>без дзвінків і хаосу</h1>
    <p>Клієнти бронюють столик прямо в Telegram — обирають місце на плані залу, дату й час. Ви бачите всі заявки в одній панелі.</p>
    <div class="hero-actions">
      <a href="/register" class="btn-primary">Підключити свій заклад</a>
      <a href="#how" class="btn-ghost">Як це працює</a>
    </div>

    <div class="mock-wrap">
      <div class="mock">
        <div class="mock-screen">
          <div class="mock-bar"></div>
          <div class="mock-row">
            <div class="mock-tbl"></div><div class="mock-tbl busy"></div><div class="mock-tbl"></div>
            <div class="mock-tbl"></div><div class="mock-tbl"></div><div class="mock-tbl busy"></div>
            <div class="mock-tbl"></div><div class="mock-tbl"></div><div class="mock-tbl"></div>
          </div>
          <div class="mock-btn"></div>
        </div>
      </div>
    </div>
  </section>

  <div class="stats">
    <div class="stat"><div class="n">&lt;60с</div><div class="l">Середній час бронювання</div></div>
    <div class="stat"><div class="n">24/7</div><div class="l">Приймає заявки без вихідних</div></div>
    <div class="stat"><div class="n">0₴</div><div class="l">Без комісії з бронювань</div></div>
  </div>

  <section class="section" id="how">
    <div class="section-head">
      <div class="eyebrow">Як це працює</div>
      <h2>Три кроки — і ваш заклад приймає бронювання</h2>
    </div>
    <div class="steps">
      <div class="step">
        <div class="num">01</div>
        <h3>Реєструєте заклад</h3>
        <p>Вказуєте назву, столи та кількість місць. Займає п'ять хвилин, без технічних знань.</p>
      </div>
      <div class="step">
        <div class="num">02</div>
        <h3>Отримуєте бота</h3>
        <p>Одразу генерується персональне посилання на Telegram-бота з вашим планом залу.</p>
      </div>
      <div class="step">
        <div class="num">03</div>
        <h3>Керуєте бронюваннями</h3>
        <p>Заявки приходять у Telegram і в панель управління. Підтверджуєте в один клік.</p>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div class="eyebrow">Можливості</div>
      <h2>Все що потрібно закладу — в одному сервісі</h2>
    </div>
    <div class="features">
      <div class="feature">
        <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/></svg></div>
        <h3>Живий план залу</h3>
        <p>Клієнт бачить які столи вільні, а які зайняті — прямо зараз, без дзвінків адміну.</p>
      </div>
      <div class="feature">
        <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>
        <h3>Захищена панель</h3>
        <p>Тільки ви маєте доступ до бронювань свого закладу — за особистим секретним ключем.</p>
      </div>
      <div class="feature">
        <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg></div>
        <h3>Миттєві сповіщення</h3>
        <p>Кожна нова заявка одразу приходить вам у Telegram — з кнопками підтвердити чи скасувати.</p>
      </div>
      <div class="feature">
        <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4.5 8-11.8A8 8 0 0 0 4 10.2C4 17.5 12 22 12 22Z"/><circle cx="12" cy="10" r="3"/></svg></div>
        <h3>Без окремого сайту</h3>
        <p>Все працює всередині Telegram — клієнту не потрібно нічого встановлювати чи реєструватись.</p>
      </div>
      <div class="feature">
        <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg></div>
        <h3>Захист від спаму</h3>
        <p>Обмеження на кількість активних бронювань і перевірку дублів — черга працює чесно.</p>
      </div>
      <div class="feature">
        <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20V10M18 20V4M6 20v-4"/></svg></div>
        <h3>Готово за хвилини</h3>
        <p>Не треба чекати розробників — заповнюєте форму й одразу отримуєте робочого бота.</p>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="cta-band">
      <h2>Готові прийняти перше бронювання?</h2>
      <p>Підключення безкоштовне і займає кілька хвилин.</p>
      <a href="/register" class="btn-primary">Підключити заклад</a>
    </div>
  </section>
</div>

<footer><span class="footer-mark"><svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="5"/><circle cx="12" cy="3" r="1.7"/><circle cx="21" cy="12" r="1.7"/><circle cx="12" cy="21" r="1.7"/><circle cx="3" cy="12" r="1.7"/></svg></span>© Stolyk · Бронювання столиків через Telegram</footer>
</body>
</html>"""


REGISTER_HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Реєстрація закладу</title>
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
  --r:16px;--r-sm:10px;
}
html,body{background:var(--bg);color:var(--ink);font-family:'Inter',-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:560px;margin:0 auto;padding:34px 18px 60px}
.head{text-align:center;margin-bottom:28px}
.head .eyebrow{font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:8px}
.head h1{font-family:'Fraunces',serif;font-size:30px;font-weight:500}
.head p{font-size:13.5px;color:var(--ink2);margin-top:8px}

.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(28,26,23,.04)}
.card h2{font-family:'Fraunces',serif;font-size:18px;font-weight:500;margin-bottom:4px}
.card .hint{font-size:12.5px;color:var(--ink2);margin-bottom:16px}

.field{margin-bottom:14px}
.field label{display:block;font-size:12px;color:var(--ink2);font-weight:500;margin-bottom:7px}
.field input{width:100%;padding:12px 14px;background:var(--bg);border:1.5px solid var(--line);border-radius:var(--r-sm);font-family:'Inter';font-size:15px;outline:none;color:var(--ink)}
.field input:focus{border-color:var(--accent);background:#fff}
.slug-preview{font-size:12.5px;margin-top:7px;padding:8px 11px;border-radius:8px;background:var(--bg);color:var(--ink2)}
.slug-preview.ok{background:var(--green-soft);color:var(--green)}
.slug-preview.bad{background:var(--red-soft);color:var(--red)}

.tbl-row{display:grid;grid-template-columns:1fr 90px 34px;gap:8px;margin-bottom:8px;align-items:center}
.tbl-row input{padding:10px 12px;background:var(--bg);border:1.5px solid var(--line);border-radius:9px;font-family:'Inter';font-size:14px;outline:none;color:var(--ink)}
.tbl-row input:focus{border-color:var(--accent);background:#fff}
.tbl-del{width:34px;height:34px;border-radius:9px;background:var(--red-soft);color:var(--red);border:none;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center}
.tbl-add{width:100%;padding:11px;border-radius:9px;border:1.5px dashed var(--line);background:transparent;color:var(--ink2);font-family:'Inter';font-size:13.5px;font-weight:500;cursor:pointer;margin-top:4px}
.tbl-add:hover{border-color:var(--accent);color:var(--accent)}

.btn-submit{width:100%;padding:16px;background:var(--accent);color:#fff;border:none;border-radius:12px;font-family:'Inter';font-size:15px;font-weight:600;cursor:pointer;margin-top:6px}
.btn-submit:disabled{opacity:.4;cursor:default}
.err{background:var(--red-soft);color:var(--red);border:1px solid var(--red-line);border-radius:10px;padding:12px 14px;font-size:13.5px;margin-bottom:16px;display:none}
.err.show{display:block}

/* success */
#success{display:none}
.success-mark{width:56px;height:56px;border-radius:50%;background:var(--green-soft);border:1.5px solid var(--green-line);display:flex;align-items:center;justify-content:center;margin:0 auto 18px}
.success-mark svg{width:24px;height:24px;color:var(--green)}
.result-row{margin-bottom:16px}
.result-row label{display:block;font-size:12px;color:var(--ink2);font-weight:500;margin-bottom:7px}
.result-box{display:flex;gap:8px}
.result-box input{flex:1;padding:12px 14px;background:var(--bg);border:1.5px solid var(--line);border-radius:var(--r-sm);font-family:'Inter';font-size:13.5px;outline:none;color:var(--ink)}
.copy-btn{padding:0 16px;border-radius:var(--r-sm);border:1.5px solid var(--line);background:#fff;color:var(--ink);font-family:'Inter';font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap}
.copy-btn:active{background:var(--accent-soft);border-color:var(--accent)}
.warn{background:#fdf6e8;border:1px solid #ecd9a8;color:#95681a;border-radius:10px;padding:12px 14px;font-size:13px;margin-top:6px}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div class="eyebrow">Бронювання столиків</div>
    <h1>Підключіть свій заклад</h1>
    <p>Заповніть форму — і одразу отримаєте готового бота та панель управління.</p>
  </div>

  <div id="form">
    <div class="err" id="err-box"></div>

    <div class="card">
      <h2>Заклад</h2>
      <div class="hint">Основна інформація про ваш ресторан чи кафе.</div>
      <div class="field">
        <label>Назва закладу</label>
        <input type="text" id="f-name" placeholder="Наприклад: Мама Піца" oninput="onNameInput()">
      </div>
      <div class="field">
        <label>Унікальне посилання</label>
        <input type="text" id="f-slug" placeholder="mama_pizza" oninput="onSlugInput()">
        <div class="slug-preview" id="slug-preview">t.me/бот?start=...</div>
      </div>
      <div class="field">
        <label>Ваш Telegram ID (адміна)</label>
        <input type="text" id="f-admin" placeholder="Напишіть @userinfobot щоб дізнатись">
      </div>
    </div>

    <div class="card">
      <h2>Столи</h2>
      <div class="hint">Додайте всі столи вашого залу: назву і кількість місць.</div>
      <div id="tables-list"></div>
      <button class="tbl-add" onclick="addTableRow()">+ Додати стіл</button>
    </div>

    <button class="btn-submit" id="btn-submit" onclick="submitRegister()">Створити бота</button>
  </div>

  <div id="success">
    <div class="success-mark">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
    </div>
    <div class="head"><h1 style="font-size:24px">Готово!</h1><p>Заклад підключено. Збережіть дані нижче.</p></div>

    <div class="card">
      <div class="result-row">
        <label>Посилання для клієнтів (бот бронювання)</label>
        <div class="result-box"><input type="text" id="r-bot" readonly><button class="copy-btn" onclick="copyField('r-bot')">Копіювати</button></div>
      </div>
      <div class="result-row">
        <label>Панель управління бронюваннями</label>
        <div class="result-box"><input type="text" id="r-admin" readonly><button class="copy-btn" onclick="copyField('r-admin')">Копіювати</button></div>
      </div>
      <div class="result-row" style="margin-bottom:0">
        <label>Секретний ключ доступу</label>
        <div class="result-box"><input type="text" id="r-key" readonly><button class="copy-btn" onclick="copyField('r-key')">Копіювати</button></div>
        <div class="warn">⚠️ Збережіть цей ключ — він більше ніде не показуватиметься. Він потрібен для входу в панель управління.</div>
      </div>
    </div>
  </div>
</div>

<script>
let tableCount = 0;

function addTableRow(name, seats) {
  tableCount++;
  const id = 'tr' + tableCount;
  const wrap = document.getElementById('tables-list');
  const row = document.createElement('div');
  row.className = 'tbl-row';
  row.id = id;
  row.innerHTML = `
    <input type="text" placeholder="Стіл ${tableCount}" value="${name || ''}">
    <input type="number" placeholder="Місць" min="1" max="30" value="${seats || ''}">
    <button class="tbl-del" onclick="document.getElementById('${id}').remove()">×</button>
  `;
  wrap.appendChild(row);
}
// стартові 4 столи для прикладу
addTableRow('Стіл 1', 2);
addTableRow('Стіл 2', 4);
addTableRow('Стіл 3', 2);
addTableRow('VIP-стіл', 6);

function slugify(s) {
  return s.toLowerCase().trim()
    .replace(/[^a-z0-9а-яіїєґ\\s_-]/g, '')
    .replace(/[\\s_]+/g, '_')
    .slice(0, 40);
}

let slugManuallyEdited = false;
function onNameInput() {
  if (!slugManuallyEdited) {
    document.getElementById('f-slug').value = slugify(document.getElementById('f-name').value);
    checkSlug();
  }
}
function onSlugInput() {
  slugManuallyEdited = true;
  checkSlug();
}

let slugTimer = null;
function checkSlug() {
  clearTimeout(slugTimer);
  const raw = document.getElementById('f-slug').value;
  const preview = document.getElementById('slug-preview');
  if (!raw.trim()) { preview.className = 'slug-preview'; preview.textContent = 't.me/бот?start=...'; return; }
  slugTimer = setTimeout(async () => {
    try {
      const res = await fetch('/api/check-slug?slug=' + encodeURIComponent(raw));
      const d = await res.json();
      if (d.available) {
        preview.className = 'slug-preview ok';
        preview.textContent = '✓ t.me/бот?start=' + d.slug;
      } else {
        preview.className = 'slug-preview bad';
        preview.textContent = d.valid ? 'Це посилання вже зайняте' : 'Некоректне посилання';
      }
    } catch(e) {}
  }, 400);
}

function showErr(msg) {
  const box = document.getElementById('err-box');
  box.textContent = msg;
  box.classList.add('show');
  window.scrollTo({top:0, behavior:'smooth'});
}

async function submitRegister() {
  const btn = document.getElementById('btn-submit');
  document.getElementById('err-box').classList.remove('show');

  const name = document.getElementById('f-name').value.trim();
  const slug = document.getElementById('f-slug').value.trim();
  const adminId = document.getElementById('f-admin').value.trim();
  const rows = document.querySelectorAll('.tbl-row');
  const tables = Array.from(rows).map(r => {
    const inputs = r.querySelectorAll('input');
    return { name: inputs[0].value.trim(), seats: parseInt(inputs[1].value) };
  });

  if (!name) return showErr('Вкажіть назву закладу.');
  if (!slug) return showErr('Вкажіть посилання закладу.');
  if (!adminId) return showErr('Вкажіть свій Telegram ID.');
  if (tables.length === 0) return showErr('Додайте хоча б один стіл.');

  btn.disabled = true;
  btn.textContent = 'Створюємо…';

  try {
    const res = await fetch('/api/register', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name, slug, adminId, tables })
    });
    const d = await res.json();
    if (!res.ok || d.error) {
      showErr(d.error || 'Щось пішло не так.');
      btn.disabled = false;
      btn.textContent = 'Створити бота';
      return;
    }
    document.getElementById('r-bot').value = d.bot_link;
    document.getElementById('r-admin').value = d.admin_url;
    document.getElementById('r-key').value = d.admin_key;
    document.getElementById('form').style.display = 'none';
    document.getElementById('success').style.display = 'block';
    window.scrollTo({top:0, behavior:'smooth'});
  } catch(e) {
    showErr('Помилка з\\'єднання. Спробуйте ще раз.');
    btn.disabled = false;
    btn.textContent = 'Створити бота';
  }
}

function copyField(id) {
  const el = document.getElementById(id);
  el.select();
  el.setSelectionRange(0, 99999);
  navigator.clipboard.writeText(el.value).catch(() => document.execCommand('copy'));
}
</script>
</body>
</html>"""


async def main():
    await db.init_db()
    await bot.delete_webhook(drop_pending_updates=True)

    # Start HTTP server
    app = web.Application()
    app.router.add_get('/', landing_page)
    app.router.add_get('/register', register_page)
    app.router.add_get('/api/check-slug', api_check_slug)
    app.router.add_post('/api/register', api_register)
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
