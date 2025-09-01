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
TOKEN = "ВАШ_ТОКЕН"  # Замените на реальный токен
MAIN_CHAT_ID = -123456789  # ID основного чата (откуда удалять)
LIST_CHAT_ID = -987654321  # ID чата со списком (где мониторим)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text(
        "🤖 Бот для управления чатом запущен!\n"
        "Используйте /help для списка команд"
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help."""
    help_text = (
        "📌 <b>Доступные команды:</b>\n\n"
        "/start - Перезапуск бота\n"
        "/help - Эта справка\n\n"
        "🔍 <b>Автоматические функции:</b>\n"
        f"• Мониторинг чата ID: <code>{LIST_CHAT_ID}</code>\n"
        f"• Удаление из чата ID: <code>{MAIN_CHAT_ID}</code>\n\n"
        "⚠️ <i>Бот должен быть администратором в обоих чатах!</i>"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

def extract_members(text: str) -> set:
    """Извлекает user_id или @username из текста."""
    user_ids = set(re.findall(r"\b\d{5,}\b", text))  # ID от 5 цифр
    usernames = set(re.findall(r"@(\w+)", text.lower()))
    return user_ids.union(usernames)

async def check_members(update: Update, context: CallbackContext) -> None:
    """Проверяет список и удаляет лишних из основного чата."""
    if update.effective_chat.id != LIST_CHAT_ID:
        return

    try:
        new_members = extract_members(update.effective_message.text)
        if not new_members:
            raise ValueError("Не найден список пользователей")

        chat = await context.bot.get_chat(MAIN_CHAT_ID)
        admins = await chat.get_administrators()
        
        current_members = {
            str(member.user.id) for member in admins
        }.union(
            {member.user.username.lower() for member in admins if member.user.username}
        )

        for member in admins:
            user_id = str(member.user.id)
            username = member.user.username.lower() if member.user.username else None

            if (user_id not in new_members) and (username not in new_members):
                try:
                    # Проверяем, не является ли пользователь создателем
                    if member.status != 'creator':
                        await context.bot.ban_chat_member(
                            chat_id=MAIN_CHAT_ID,
                            user_id=member.user.id
                        )
                        logger.info(f"❌ Удален: {username or user_id}")
                    else:
                        logger.warning(f"⚠️ Нельзя удалить создателя: {username or user_id}")
                except Exception as e:
                    logger.error(f"🚫 Ошибка удаления {username or user_id}: {e}")

    except Exception as e:
        logger.error(f"🔥 Ошибка обработки списка: {e}")

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Обработчик сообщений в чате со списком
    application.add_handler(
        MessageHandler(
            filters.Chat(chat_id=LIST_CHAT_ID) & filters.TEXT,
            check_members
        )
    )

    # Запуск бота
    logger.info("🟢 Бот запущен и ожидает команд...")
    application.run_polling()

if __name__ == "__main__":
    main()
