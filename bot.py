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
    level=logging.DEBUG,  # NEW: Изменено на DEBUG для подробных логов
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# NEW: Глобальная переменная для отслеживания состояния
LAST_PROCESSED_MESSAGE = None

async def test_parse(update: Update, context: CallbackContext):
    test_text = """Актуальные участники:
@A2nn3Ma3l
333352583954"""
    
    members = extract_members(test_text)
    await update.message.reply_text(f"Результат парсинга:\n{members}")

async def log_all_updates(update: Update, context: CallbackContext):  # NEW
    """Логирует все входящие обновления"""
    logger.debug(f"Получено обновление: {update.to_dict()}")

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 Бот для управления чатом запущен!\n"
        "Отправьте /help для списка команд"
    )
    logger.info(f"Обработана команда /start от {update.effective_user.id}")

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
    logger.info(f"Обработана команда /help от {update.effective_user.id}")

def extract_members(text: str) -> set:
    """Извлекает user_id и @username из текста с подробным логированием"""
    global LAST_PROCESSED_MESSAGE  # NEW
    
    logger.info(f"[extract_members] Начало обработки текста:\n{text[:200]}...")
    LAST_PROCESSED_MESSAGE = text[:200]  # NEW: Сохраняем последнее сообщение
    
    members = set()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        logger.warning("[extract_members] Получен пустой текст для обработки")
        return members

    logger.info(f"[extract_members] Обнаружено строк: {len(lines)}")
    
    # Пропускаем строку с заголовком
    if len(lines) > 1:
        logger.debug(f"[extract_members] Пропускаем заголовок: '{lines[0]}'")
    
    processed_count = 0
    invalid_count = 0
    
    for line in lines[1:]:
        try:
            logger.debug(f"[extract_members] Обработка строки: '{line}'")
            
            if line.startswith('@'):
                username = line[1:].lower()
                if re.fullmatch(r'[a-z0-9_]{5,32}', username):
                    members.add(username)
                    logger.debug(f"[extract_members] Добавлен username: {username}")
                    processed_count += 1
                else:
                    logger.warning(f"[extract_members] Некорректный username: {line}")
                    invalid_count += 1
                    
            elif re.fullmatch(r'\d{5,}', line):
                members.add(line)
                logger.debug(f"[extract_members] Добавлен user_id: {line}")
                processed_count += 1
            else:
                logger.warning(f"[extract_members] Неопознанный формат: '{line}'")
                invalid_count += 1
                
        except Exception as e:
            logger.error(f"[extract_members] Ошибка обработки строки: {str(e)}")
            invalid_count += 1

    logger.info(
        f"[extract_members] Результат: успешно {processed_count}, "
        f"ошибок {invalid_count}, всего {len(members)}"
    )
    return members

async def check_members(update: Update, context: CallbackContext) -> None:
    """Обрабатывает сообщения со списком участников"""
    global LAST_PROCESSED_MESSAGE  # NEW
    
    try:
        logger.info(f"[check_members] Начало обработки сообщения в чате {update.effective_chat.id}")
        
        # NEW: Проверка текста сообщения
        if not update.message or not update.message.text:
            logger.warning("[check_members] Пустое сообщение или без текста")
            return
            
        # NEW: Логирование полного сообщения
        logger.debug(f"[check_members] Полный текст сообщения:\n{update.message.text}")
        
        # Пропускаем команды
        if update.message.text.startswith('/'):
            logger.debug("[check_members] Пропуск командного сообщения")
            return
            
        # Проверяем чат
        if update.effective_chat.id != LIST_CHAT_ID:
            logger.warning(
                f"[check_members] Игнорируем чужой чат {update.effective_chat.id} "
                f"(ожидаем {LIST_CHAT_ID})"
            )
            return

        # NEW: Проверка прав бота
        try:
            chat = await context.bot.get_chat(MAIN_CHAT_ID)
            bot_member = await chat.get_member(context.bot.id)
            if not bot_member.can_restrict_members:
                logger.error("[check_members] У бота нет прав на удаление участников")
                await update.message.reply_text("⚠️ У меня нет прав на удаление!")
                return
        except Exception as e:
            logger.error(f"[check_members] Ошибка проверки прав: {str(e)}")
            return

        # Извлекаем участников
        new_members = extract_members(update.message.text)
        if not new_members:
            logger.warning("[check_members] Не удалось извлечь участников")
            await update.message.reply_text("❌ Не найден список участников")
            return

        logger.info(f"[check_members] Извлечено участников: {len(new_members)}")

        # Получаем текущих администраторов
        admins = await chat.get_administrators()
        logger.info(f"[check_members] Найдено администраторов: {len(admins)}")

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
                        logger.info(f"[check_members] Удален: {username or user_id}")
                except Exception as e:
                    logger.error(f"[check_members] Ошибка удаления: {str(e)}")

        if removed:
            await update.message.reply_text(f"✅ Удалены: {', '.join(removed)}")
        else:
            await update.message.reply_text("ℹ️ Нет пользователей для удаления")

    except Exception as e:
        logger.error(f"[check_members] Критическая ошибка: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка при обработке")

async def test_command(update: Update, context: CallbackContext) -> None:
    """Тестовая команда для проверки"""
    logger.info("[test_command] Запуск тестовой проверки")
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

async def debug_command(update: Update, context: CallbackContext):  # NEW
    """Команда для отладки"""
    debug_info = (
        f"Состояние бота:\n"
        f"Последнее обработанное сообщение:\n{LAST_PROCESSED_MESSAGE or 'Нет данных'}\n"
        f"LIST_CHAT_ID: {LIST_CHAT_ID}\n"
        f"MAIN_CHAT_ID: {MAIN_CHAT_ID}"
    )
    await update.message.reply_text(f"<pre>{debug_info}</pre>", parse_mode='HTML')

def main() -> None:
    """Запуск бота"""
    try:
        logger.info("="*50)
        logger.info("Запуск бота")
        logger.info(f"LIST_CHAT_ID: {LIST_CHAT_ID}")
        logger.info(f"MAIN_CHAT_ID: {MAIN_CHAT_ID}")

        application = Application.builder().token(TOKEN).build()

        # NEW: Обработчик всех входящих сообщений для диагностики
        application.add_handler(MessageHandler(filters.ALL, log_all_updates), group=-1)

        # Обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("test", test_command))
        application.add_handler(CommandHandler("debug", debug_command))  # NEW

        # Обработчик сообщений
        application.add_handler(MessageHandler(
            filters.Chat(chat_id=LIST_CHAT_ID) & (filters.TEXT | filters.CAPTION),
# filters.Chat(LIST_CHAT_ID) & filters.TEXT & ~filters.COMMAND,
            check_members
        ), group=1)

        logger.info("Бот успешно запущен")
        application.run_polling()

    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
