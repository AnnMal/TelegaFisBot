import logging
import re
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
MAIN_CHAT_ID = -4884863804  # Чат, откуда будем удалять
LIST_CHAT_ID = -1002900105796  # Чат с актуальными участниками

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

# Глобальные переменные
LAST_PROCESSED_MESSAGE = None

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def extract_members(text: str) -> set:
    """Извлекает user_id и @username из текста"""
    global LAST_PROCESSED_MESSAGE
    logger.info(f"[extract_members] Обработка текста:\n{text[:200]}...")
    LAST_PROCESSED_MESSAGE = text[:200]
    
    members = set()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines or not lines[0].lower().startswith('актуальные участники'):
        logger.warning("Не найден заголовок 'Актуальные участники'")
        return members

    for line in lines[1:]:  # Пропускаем первую строку (заголовок)
        line = line.strip()
        try:
            if line.startswith('@'):
                username = line[1:].lower()
                if re.fullmatch(r'[a-z0-9_]{5,32}', username):
                    members.add(username)
                    logger.debug(f"Добавлен username: {username}")
            elif re.fullmatch(r'\d{5,}', line):
                members.add(line)
                logger.debug(f"Добавлен user_id: {line}")
        except Exception as e:
            logger.error(f"Ошибка обработки строки: {e}")

    logger.info(f"Успешно извлечено участников: {len(members)}")
    return members

# ========== ОБРАБОТЧИКИ КОМАНД ==========

async def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 Бот для управления участниками чата запущен!\n"
        "Отправьте /help для справки"
    )
    logger.info(f"Обработана команда /start от {update.effective_user.id}")

async def help_command(update: Update, context: CallbackContext):
    """Обработчик команды /help"""
    help_text = (
        "📌 <b>Команды бота:</b>\n\n"
        "/start - Перезапуск бота\n"
        "/help - Справка\n"
        "/test - Проверка парсера\n"
        "/debug - Отладочная информация\n\n"
        "📋 <b>Формат списка участников:</b>\n"
        "Актуальные участники:\n"
        "@username1\n"
        "123456789\n"
        "@username2"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')
    logger.info(f"Обработана команда /help от {update.effective_user.id}")

async def ping(update: Update, context: CallbackContext):
    """Проверка работы бота"""
    await update.message.reply_text("🟢 Бот активен!")
    logger.info(f"Команда /ping от {update.effective_user.id}")

async def test_command(update: Update, context: CallbackContext):
    """Тест парсера"""
    test_msg = """Актуальные участники:
@testuser
123456789"""
    members = extract_members(test_msg)
    await update.message.reply_text(f"Тестовые данные:\n{test_msg}\n\nРезультат:\n{members}")
    logger.info("Выполнен тест парсера")

async def debug_command(update: Update, context: CallbackContext):
    """Отладочная информация"""
    debug_info = (
        f"<b>Состояние бота:</b>\n"
        f"Последнее сообщение:\n<code>{LAST_PROCESSED_MESSAGE or 'Нет данных'}</code>\n\n"
        f"<b>Настройки чатов:</b>\n"
        f"LIST_CHAT_ID: {LIST_CHAT_ID}\n"
        f"MAIN_CHAT_ID: {MAIN_CHAT_ID}"
    )
    await update.message.reply_text(debug_info, parse_mode='HTML')
    logger.info("Выполнена команда /debug")

# ========== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ ==========

async def check_members(update: Update, context: CallbackContext):
    """Обработка сообщений со списком участников"""
    try:
        logger.info(f"Получено сообщение в чате {update.effective_chat.id}")
        
        # Проверяем чат-источник
        if update.effective_chat.id != LIST_CHAT_ID:
            logger.warning(f"Игнорируем сообщение из чужого чата {update.effective_chat.id}")
            return

        # Проверяем тип сообщения
        if not update.message or not update.message.text:
            logger.warning("Пустое сообщение или без текста")
            return

        # Пропускаем команды
        if update.message.text.startswith('/'):
            logger.debug("Пропускаем командное сообщение")
            return

        # Проверяем формат сообщения
        if not update.message.text.startswith('Актуальные участники'):
            logger.warning("Неверный формат сообщения")
            await update.message.reply_text(
                "⚠️ Неверный формат. Должно быть:\n"
                "Актуальные участники:\n"
                "@username1\n"
                "123456789"
            )
            return

        logger.info(f"Обработка сообщения:\n{update.message.text[:200]}...")

        # Извлекаем участников
        new_members = extract_members(update.message.text)
        if not new_members:
            await update.message.reply_text("❌ Не удалось извлечь участников из списка")
            return

        # Проверяем права бота в целевом чате
        try:
            main_chat = await context.bot.get_chat(MAIN_CHAT_ID)
            bot_member = await main_chat.get_member(context.bot.id)
            
            if not bot_member.can_restrict_members:
                await update.message.reply_text("⛔ У бота нет прав на удаление участников!")
                return
        except Exception as e:
            logger.error(f"Ошибка проверки прав: {str(e)}")
            await update.message.reply_text("⚠️ Ошибка проверки прав бота")
            return

        # Получаем текущих администраторов
        admins = await main_chat.get_administrators()
        removed = []
        errors = []

        for member in admins:
            # Не удаляем создателя чата
            if member.status == 'creator':
                continue

            user_id = str(member.user.id)
            username = member.user.username.lower() if member.user.username else None

            # Проверяем наличие в списке
            if (user_id not in new_members) and (username not in new_members):
                try:
                    await context.bot.ban_chat_member(
                        chat_id=MAIN_CHAT_ID,
                        user_id=member.user.id
                    )
                    removed.append(f"@{member.user.username}" if member.user.username else user_id)
                    logger.info(f"Удален участник: {user_id}")
                except Exception as e:
                    errors.append(f"{user_id}: {str(e)}")
                    logger.error(f"Ошибка удаления {user_id}: {str(e)}")

        # Формируем отчет
        report = []
        if removed:
            report.append(f"✅ Удалены: {', '.join(removed)}")
        if errors:
            report.append(f"❌ Ошибки: {len(errors)}")
        if not removed and not errors:
            report.append("ℹ️ Нет пользователей для удаления")

        await update.message.reply_text("\n".join(report))

    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка при обработке")

async def log_all_updates(update: Update, context: CallbackContext):
    """Логирует все входящие сообщения для отладки"""
    logger.debug(f"Update: {update.to_dict()}")

# ========== ЗАПУСК БОТА ==========

def main():
    """Запускает бота"""
    try:
        logger.info("="*50)
        logger.info("Запуск бота FISExit")
        logger.info(f"Чат с списком: {LIST_CHAT_ID}")
        logger.info(f"Целевой чат: {MAIN_CHAT_ID}")

        # Создаем приложение
        application = Application.builder().token(TOKEN).build()

        # Обработчики команд
        cmd_handlers = [
            CommandHandler("start", start),
            CommandHandler("help", help_command),
            CommandHandler("ping", ping),
            CommandHandler("test", test_command),
            CommandHandler("debug", debug_command)
        ]
        for handler in cmd_handlers:
            application.add_handler(handler)

        # Обработчик сообщений
        application.add_handler(
            MessageHandler(
                filters.Chat(chat_id=LIST_CHAT_ID) & filters.TEXT,
                check_members
            ),
            group=1
        )

        # Логирование всех входящих сообщений (для отладки)
        application.add_handler(
            MessageHandler(filters.ALL, log_all_updates),
            group=-1
        )

        logger.info("Бот запущен в режиме polling...")
        application.run_polling()

    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
