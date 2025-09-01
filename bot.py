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

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 Бот для управления чатом запущен!\n"
        "Отправьте /help для списка команд"
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help"""
    help_text = (
        "📌 <b>Доступные команды:</b>\n\n"
        "/start - Перезапуск бота\n"
        "/help - Эта справка\n"
        "/test - Тестовая проверка\n\n"
        "📋 <b>Формат списка участников:</b>\n"
        "Актуальные участники:\n"
        "@username1\n"
        "123456789"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

def extract_members(text: str) -> set:
    """Извлекает user_id и @username из текста"""
    members = set()
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    logger.info(f"Извлекаем user_id и @username из текста")
    
    # Пропускаем строку с заголовком
    for line in lines[1:]:
        if line.startswith('@'):
            members.add(line[1:].lower())
        elif re.fullmatch(r'\d{5,}', line):
            members.add(line)
    
    return members

async def check_members(update: Update, context: CallbackContext) -> None:
    """Обрабатывает только сообщения со списком участников"""
    try:
        # Пропускаем команды
        if update.message.text.startswith('/'):
            return
            
        # Проверяем чат
        if update.effective_chat.id != LIST_CHAT_ID:
            return

        logger.info(f"Получен список: {update.message.text}")
        
        # Извлекаем участников
        new_members = extract_members(update.message.text)
        if not new_members:
            await update.message.reply_text("❌ Не найден список участников")
            return

        # Получаем текущих администраторов
        chat = await context.bot.get_chat(MAIN_CHAT_ID)
        admins = await chat.get_administrators()
        
        # Проверяем права бота
        bot_member = await chat.get_member(context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("⚠️ У меня нет прав на удаление!")
            return

        # Поиск пользователей для удаления
        removed = []
        for member in admins:
            user_id = str(member.user.id)
            username = member.user.username.lower() if member.user.username else None
            
            if (user_id not in new_members) and (username not in new_members):
                try:
                    if member.status != 'creator':
                        await context.bot.ban_chat_member(
                            chat_id=MAIN_CHAT_ID,
                            user_id=member.user.id
                        )
                        removed.append(username or user_id)
                except Exception as e:
                    logger.error(f"Ошибка удаления: {e}")

        if removed:
            await update.message.reply_text(f"✅ Удалены: {', '.join(removed)}")
        else:
            await update.message.reply_text("ℹ️ Нет пользователей для удаления")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при обработке")

async def test_command(update: Update, context: CallbackContext) -> None:
    """Тестовая команда для проверки"""
    test_msg = """Актуальные участники:
@test_user
123456789"""
    
    fake_update = Update(
        update_id=update.update_id + 1,
        message=Message(
            message_id=update.message.message_id + 1,
            date=datetime.now(),
            chat=Chat(id=LIST_CHAT_ID, type='supergroup'),
            text=test_msg
        )
    )
    await check_members(fake_update, context)

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("test", test_command))

    # Обработчик сообщений (исключает команды)
    application.add_handler(MessageHandler(
        filters.Chat(LIST_CHAT_ID) & filters.TEXT & ~filters.COMMAND,
        check_members
    ))

    logger.info("Бот запущен и готов к работе")
    application.run_polling()

if __name__ == "__main__":
    main()
