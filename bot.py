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
TOKEN = "8285946823:AAE6mT6BtJsOkTQFsP-IrBHonhtaUaJAg8g"
MAIN_CHAT_ID = -4884863804  # ID основного чата (откуда удалять)
LIST_CHAT_ID = -4960077583  # ID чата со списком (где мониторим)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text("🤖 Бот запущен! Ожидаю обновлений списка...")

def extract_members(text: str) -> set:
    """Извлекает user_id или @username из текста."""
    user_ids = set(re.findall(r"\b\d{5,}\b", text))  # ID обычно от 5 цифр
    usernames = set(re.findall(r"@(\w+)", text.lower()))
    return user_ids.union(usernames)

async def check_members(update: Update, context: CallbackContext) -> None:
    """Проверяет список и удаляет лишних из основного чата."""
    if update.effective_chat.id != LIST_CHAT_ID:
        return

    try:
        new_members = extract_members(update.effective_message.text)
        if not new_members:
            raise ValueError("Не найден список пользователей.")

        chat = await context.bot.get_chat(MAIN_CHAT_ID)
        chat_members = await chat.get_administrators()
        
        current_members = {
            str(member.user.id) for member in chat_members
        }.union(
            {member.user.username.lower() for member in chat_members if member.user.username}
        )

        for member in chat_members:
            user_id = str(member.user.id)
            username = member.user.username.lower() if member.user.username else None
            
            if (user_id not in new_members) and (username not in new_members):
                try:
                    await context.bot.ban_chat_member(
                        chat_id=MAIN_CHAT_ID,
                        user_id=member.user.id
                    )
                    logger.info(f"❌ Удален: {username or user_id}")
                except Exception as e:
                    logger.error(f"Ошибка удаления {username or user_id}: {e}")

    except Exception as e:
        logger.error(f"Ошибка обработки списка: {e}")

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))

    # Обработчик сообщений в чате со списком
    application.add_handler(
        MessageHandler(
            filters.Chat(chat_id=LIST_CHAT_ID) & filters.TEXT,
            check_members
        )
    )

    # Запуск бота
    application.run_polling()
    logger.info("🟢 Бот запущен и слушает обновления...")

if __name__ == "__main__":
    main()
