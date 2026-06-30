import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # твій Telegram ID
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-webapp.vercel.app")
ADMIN_KEY = os.getenv("ADMIN_KEY", "")  # секретний ключ для входу в адмін-панель
