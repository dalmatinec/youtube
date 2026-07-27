import os

# Токен от @BotFather. Можно вписать прямо сюда либо задать переменную окружения BOT_TOKEN.
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER")

# Сколько скачиваний разрешено одному юзеру за 24 часа (бесплатный тариф)
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "15"))

# Куда временно сохранять файлы перед отправкой (потом удаляются)
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")

# Обычный Bot API не пропускает файлы больше 50 МБ
MAX_TELEGRAM_FILE_MB = 50

# Путь к базе со статистикой/лимитами/премиумом
DB_PATH = os.getenv("DB_PATH", "bot.db")

# user_id админов (через запятую), например: 12345,67890
ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

# --- Премиум-подписка ---
PREMIUM_DAYS = int(os.getenv("PREMIUM_DAYS", "30"))

# Цена в Telegram Stars за PREMIUM_DAYS дней
STARS_PRICE = int(os.getenv("STARS_PRICE", "150"))

# Куда писать при оплате вручную (юзеру покажется эта контактная строка)
ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "@твой_username")

# Сколько скачиваний обрабатывается одновременно (воркеров в очереди).
# Премиум-юзеры получают приоритет внутри этой очереди, а не безлимитную параллельность.
CONCURRENT_DOWNLOADS = int(os.getenv("CONCURRENT_DOWNLOADS", "2"))
