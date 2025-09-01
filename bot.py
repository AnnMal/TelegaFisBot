import logging
import re
from telegram import Update, ChatPermissions
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

# Настройки бота
TOKEN = "ВАШ_ТОКЕН_БОТА"  # Замените на реальный токен
MAIN_CHAT_ID = -1001234567890  # ID основного чата (откуда удалять)
LIST_CHAT_ID = -1009876543210  # ID чата со списком (где мониторим)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    update.message.reply_text("🤖 Бот запущен! Ожидаю обновлений списка...")

def extract_members(text: str) -> set:
    """Извлекает user_id или @username из текста."""
    # Ищем ID (цифры) и юзернеймы (@example)
    user_ids = set(re.findall(r"\b\d{5,}\b", text))  # ID обычно от 5 цифр
    usernames = set(re.findall(r"@(\w+)", text.lower()))
    return user_ids.union(usernames)

def check_members(update: Update, context: CallbackContext) -> None:
    """Проверяет список и удаляет лишних из основного чата."""
    if update.effective_chat.id != LIST_CHAT_ID:
        return  # Игнорируем другие чаты

    try:
        # Получаем текущий список из сообщения
        new_members = extract_members(update.effective_message.text)
        if not new_members:
            raise ValueError("Не найден список пользователей.")

        # Получаем участников основного чата
        chat_members = context.bot.get_chat_administrators(MAIN_CHAT_ID)
        current_members = {
            str(member.user.id) for member in chat_members
        }.union(
            {member.user.username.lower() for member in chat_members if member.user.username}
        )

        # Удаляем тех, кого нет в новом списке
        for member in chat_members:
            user_id = str(member.user.id)
            username = member.user.username.lower() if member.user.username else None

            if (user_id not in new_members) and (username not in new_members):
                try:
                    context.bot.ban_chat_member(MAIN_CHAT_ID, member.user.id)
                    logger.info(f"❌ Удален: {username or user_id}")
                except Exception as e:
                    logger.error(f"Ошибка удаления {username or user_id}: {e}")

    except Exception as e:
        logger.error(f"Ошибка обработки списка: {e}")

def main() -> None:
    """Запуск бота."""
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Обработчики команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))

    # Обработчик сообщений в чате со списком
    dispatcher.add_handler(
        MessageHandler(
            Filters.chat(LIST_CHAT_ID) & Filters.text,
            check_members
        )
    )

    # Запуск бота в режиме polling
    updater.start_polling()
    logger.info("🟢 Бот запущен и слушает обновления...")
    updater.idle()

if __name__ == "__main__":
    main()
