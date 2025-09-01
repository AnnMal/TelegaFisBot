import logging
import re
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

# Настройки бота
TOKEN = "8285946823:AAE6mT6BtJsOkTQFsP-IrBHonhtaUaJAg8g"  # Замените на реальный токен
MAIN_CHAT_ID = -4884863804  # ID основного чата (откуда удалять)
LIST_CHAT_ID = -1002900105796  # ID чата со списком (где мониторим)

# Настройка логов (ДВОЙНОЕ ЛОГИРОВАНИЕ)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),  # Запись в файл
        logging.StreamHandler()  # Вывод в консоль
    ]
)
logger = logging.getLogger(__name__)

# Для удобного чтения логов в реальном времени
def tail_logs():
    """Генератор для чтения логов в реальном времени"""
    with open('bot.log', 'r', encoding='utf-8') as log_file:
        log_file.seek(0, 2)  # Перемещаемся в конец файла
        while True:
            line = log_file.readline()
            if not line:
                continue
            yield line.strip()

# NEW: Команда для чтения логов
async def show_logs(update: Update, context: CallbackContext):
    """Отправка последних 10 строк лога"""
    try:
        with open('bot.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()[-10:]
            await update.message.reply_text(f"📋 Последние логи:\n```\n{''.join(lines)}\n```", 
                                          parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка чтения логов: {e}")

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text(
        "🤖 Бот для управления чатом запущен!\n"
        "Используйте /help для списка команд"
    )
    logger.info("Бот запущен через команду /start")  # Пример записи в лог

# ... (остальные функции из предыдущего кода остаются без изменений) ...

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check_reaction", check_reaction))
    application.add_handler(CommandHandler("logs", show_logs))  # NEW

    # Обработчик сообщений в чате со списком
    application.add_handler(
        MessageHandler(
            filters.Chat(chat_id=LIST_CHAT_ID) & filters.TEXT,
            check_members
        )
    )

    # Запуск бота
    logger.info("🟢🟢🟢 Бот запущен и ожидает команд...")
    application.run_polling()

if __name__ == "__main__":
    main()
