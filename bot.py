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

# Глобальная переменная
LAST_PROCESSED_MESSAGE = None

# ========== ОБРАБОТЧИКИ КОМАНД ==========

async def ping(update: Update, context: CallbackContext):
    """Обработчик команды ping"""
    await update.message.reply_text("Pong! Бот активен в этом чате.")
    logger.info(f"Команда /ping от {update.effective_user.id}")

async def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 Бот для управления чатом запущен!\n"
        "Отправьте /help для списка команд"
    )
    logger.info(f"Обработана команда /start от {update.effective_user.id}")

async def help_command(update: Update, context: CallbackContext):
    """Обработчик команды /help"""
    help_text = (
        "📌 <b>Доступные команды:</b>\n\n"
        "/start - Перезапуск бота\n"
        "/help - Эта справка\n"
        "/ping - Проверка активности\n"
        "/test - Тест парсера\n"
        "/debug - Информация для отладки\n\n"
        "📋 <b>Формат списка участников:</b>\n"
        "Актуальные участники:\n"
        "@username1\n"
        "123456789"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')
    logger.info(f"Обработана команда /help от {update.effective_user.id}")

async def test_command(update: Update, context: CallbackContext):
    """Тестовая команда для проверки парсера"""
    logger.info("[test_command] Запуск тестовой проверки")
    test_msg = """Актуальные участники:
@test_user
123456789"""
    members = extract_members(test_msg)
    await update.message.reply_text(f"Тестовые данные:\n{test_msg}\n\nРезультат:\n{members}")

async def debug_command(update: Update, context: CallbackContext):
    """Команда для отладки"""
    debug_info = (
        f"Состояние бота:\n"
        f"Последнее обработанное сообщение:\n{LAST_PROCESSED_MESSAGE or 'Нет данных'}\n"
        f"LIST_CHAT_ID: {LIST_CHAT_ID}\n"
        f"MAIN_CHAT_ID: {MAIN_CHAT_ID}"
    )
    await update.message.reply_text(f"<pre>{debug_info}</pre>", parse_mode='HTML')

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========

def extract_members(text: str) -> set:
    """Извлекает user_id и @username из текста"""
    global LAST_PROCESSED_MESSAGE
    logger.info(f"[extract_members] Начало обработки текста:\n{text[:200]}...")
    LAST_PROCESSED_MESSAGE = text[:200]
    
    members = set()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        logger.warning("[extract_members] Пустой текст")
        return members

    # Пропускаем заголовок
    for line in lines[1:]:
        try:
            if line.startswith('@'):
                username = line[1:].lower()
                if re.fullmatch(r'[a-z0-9_]{5,32}', username):
                    members.add(username)
            elif re.fullmatch(r'\d{5,}', line):
                members.add(line)
        except Exception as e:
            logger.error(f"Ошибка обработки строки: {e}")

    logger.info(f"[extract_members] Найдено участников: {len(members)}")
    return members

async def check_members(update: Update, context: CallbackContext):
    """Обрабатывает сообщения со списком участников"""
    global LAST_PROCESSED_MESSAGE
    
    try:
        # Проверка чата
        if update.effective_chat.id != LIST_CHAT_ID:
            logger.warning(f"Игнорируем чужой чат {update.effective_chat.id}")
            return

        # Проверка типа сообщения
        if not update.message or not update.message.text:
            logger.warning("Пустое сообщение или без текста")
            return

        # Пропускаем команды
        if update.message.text.startswith('/'):
            return

        logger.info(f"Обработка сообщения в чате {update.effective_chat.id}")

        # Извлекаем участников
        new_members = extract_members(update.message.text)
        if not new_members:
            await update.message.reply_text("❌ Не найден список участников")
            return

        # Проверяем права бота
        try:
            chat = await context.bot.get_chat(MAIN_CHAT_ID)
            bot_member = await chat.get_member(context.bot.id)
            if not bot_member.can_restrict_members:
                await update.message.reply_text("⚠️ Нет прав на удаление!")
                return
        except Exception as e:
            logger.error(f"Ошибка проверки прав: {e}")
            return

        # Получаем администраторов
        admins = await chat.get_administrators()
        removed = []

        for member in admins:
            if member.status == 'creator':
                continue
                
            user_id = str(member.user.id)
            username = member.user.username.lower() if member.user.username else None

            if (user_id not in new_members) and (username not in new_members):
                try:
                    await context.bot.ban_chat_member(MAIN_CHAT_ID, member.user.id)
                    removed.append(username or user_id)
                except Exception as e:
                    logger.error(f"Ошибка удаления {user_id}: {e}")

        if removed:
            await update.message.reply_text(f"✅ Удалены: {', '.join(removed)}")
        else:
            await update.message.reply_text("ℹ️ Нет пользователей для удаления")

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ошибка обработки")

# ========== ЗАПУСК БОТА ==========

def main() -> None:
    """Запуск бота"""
    try:
        logger.info("="*50)
        logger.info("Запуск бота")
        logger.info(f"LIST_CHAT_ID: {LIST_CHAT_ID}")
        logger.info(f"MAIN_CHAT_ID: {MAIN_CHAT_ID}")

        application = Application.builder().token(TOKEN).build()

        # Обработчики команд
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

        logger.info("Бот успешно запущен")
        application.run_polling()

    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
