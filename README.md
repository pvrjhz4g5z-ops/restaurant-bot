# 🍽️ Restaurant Booking Bot

Telegram-бот для бронювання столиків з WebApp-інтерфейсом.

## Структура проекту

```
restaurant-bot/
├── bot.py          # Головний файл бота
├── database.py     # Робота з базою даних
├── config.py       # Налаштування (токен, admin ID)
├── requirements.txt
├── Procfile        # Для Railway
└── webapp/
    └── index.html  # WebApp (план столів + форма)
```

## Крок 1 — Налаштуй бота в BotFather

1. Відкрий [@BotFather](https://t.me/BotFather)
2. `/newbot` → придумай назву і username
3. Збережи токен
4. `/mybots` → твій бот → **Bot Settings** → **Menu Button** → встанови URL WebApp

## Крок 2 — Захости WebApp

Найпростіше — **Vercel** (безкоштовно):
1. Зареєструйся на [vercel.com](https://vercel.com)
2. Завантаж папку `webapp/`
3. Отримаєш URL типу `https://your-app.vercel.app`

Або додай як статичний сервіс на Railway.

## Крок 3 — Деплой бота на Railway

1. Створи новий проект на [railway.app](https://railway.app)
2. Завантаж файли бота (без папки webapp)
3. Додай Environment Variables:

```
BOT_TOKEN=твій_токен_від_BotFather
ADMIN_ID=твій_telegram_id (дізнатись у @userinfobot)
WEBAPP_URL=https://your-app.vercel.app
```

4. Railway сам запустить бота через Procfile

## Крок 4 — Дізнайся свій Telegram ID

Напиши [@userinfobot](https://t.me/userinfobot) — він поверне твій ID.
Постав його в ADMIN_ID.

## Як це працює

1. Клієнт пише `/start` боту
2. Бот показує кнопку "Забронювати столик"
3. Відкривається WebApp (plan залу)
4. Клієнт вибирає стіл → дату/час → заповнює форму
5. Дані летять боту → бот зберігає в БД
6. Клієнт отримує підтвердження
7. Адмін отримує повідомлення з кнопками ✅/❌

## Кастомізація столів

Щоб змінити розташування столів — редагуй `webapp/index.html`.
Столики в SVG позначені як `<g class="table-free" data-id="..." data-name="..." data-seats="...">`.
Зайняті столики не мають класу `table-free`.
