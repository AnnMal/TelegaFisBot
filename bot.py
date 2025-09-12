import logging
import re
from datetime import datetime
from telegram import Update, Message, Chat
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

# Настройки бота
TOKEN = "8285946823:AAE6mT6BtJsOkTQFsP-IrBHonhtaUaJAg8g"
MAIN_CHAT_ID = -4884863804
LIST_CHAT_ID = -1002900105796

# Настройка логов
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

LAST_PROCESSED_MESSAGE = None

async def ping(update: Update, context: CallbackContext):
    await update.message.reply_text("Pong! Бот активен в этом чате.")

# ... (остальные функции остаются без изменений, как в вашем коде)

def main() -> None:
    try:
        logger.info("="*50)
        logger.info("Запуск бота")
        application = Application.builder().token(TOKEN).build()
        
        # Обработчики
        application.add_handler(CommandHandler("ping", ping))
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("test", test_command))
        application.add_handler(CommandHandler("debug", debug_command))
        
        # Обработчик сообщений
        application.add_handler(MessageHandler(
            filters.Chat(chat_id=LIST_CHAT_ID) & (filters.TEXT | filters.CAPTION),
            check_members
        ), group=1)
        
        application.run_polling()
    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
