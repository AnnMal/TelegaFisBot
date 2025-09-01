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

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def debug_handler(update: Update, context: CallbackContext):
    logger.info(f"Получено сообщение в чате {update.effective_chat.id}: {update.effective_message.text}")

async def post_init(application: Application) -> None:
    """Выполняется после инициализации бота."""
    await application.bot.send_message(
        chat_id=LIST_CHAT_ID,
        text="🔔 Бот начал мониторинг этого чата!\n"
             "Отправьте список в формате:\n"
             "Актуальные участники:\n"
             "@username1\n"
             "123456789"
    )
    logger.info("Инициализация завершена, уведомление отправлено")

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text("🤖 Бот запущен! Используйте /help")
    logger.info(f"Получена команда /start от {update.effective_user.id}")

async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help."""
    help_text = (
        "📌 <b>Доступные команды:</b>\n\n"
        "/start - Перезапуск бота\n"
        "/help - Справка\n"
        "/logs - Показать логи\n\n"
        f"Мониторинг чата: <code>{LIST_CHAT_ID}</code>"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

def extract_members(text: str) -> set:
    """Извлекает user_id или @username из текста."""
    user_ids = set(re.findall(r'(?<!\d)\d{5,}(?!\d)', text))
    usernames = set(re.findall(r'@([a-zA-Z0-9_]{5,32})\b', text))
    return user_ids.union(usernames)

async def check_members(update: Update, context: CallbackContext) -> None:
    """Проверяет список и удаляет лишних."""
    try:
        new_members = extract_members(update.effective_message.text)
        if not new_members:
            await update.message.reply_text("⚠️ Не найден список пользователей!")
            return

        chat = await context.bot.get_chat(MAIN_CHAT_ID)
        admins = await chat.get_administrators()
        
        for member in admins:
            user_id = str(member.user.id)
            username = (member.user.username or "").lower()
            
            if (user_id not in new_members) and (username not in new_members):
                try:
                    if member.status != 'creator':
                        await context.bot.ban_chat_member(MAIN_CHAT_ID, member.user.id)
                        logger.info(f"Удален: {username or user_id}")
                except Exception as e:
                    logger.error(f"Ошибка удаления: {e}")

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")



def main() -> None:
    """Запуск бота."""
    application = Application.builder() \
        .token(TOKEN) \
        .post_init(post_init) \
        .build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Обработчик сообщений
    application.add_handler(
        MessageHandler(
            filters.Chat(chat_id=LIST_CHAT_ID) & filters.TEXT,
            check_members
        )
    )

    # В main() добавьте перед run_polling():
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, debug_handler), group=-1)

    logger.info("🟢🟢🟢 Запускаю бота...")
    application.run_polling()

if __name__ == "__main__":
    main()
