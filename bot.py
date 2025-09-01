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
        logger.info(f"Проверяю сообщение в чате {update.effective_chat.id}")
        
        # Проверяем, что сообщение из нужного чата
        if update.effective_chat.id != LIST_CHAT_ID:
            logger.warning(f"Игнорирую сообщение из чата {update.effective_chat.id} (ожидал {LIST_CHAT_ID})")
            return

        # Логируем сырые данные
        raw_text = update.effective_message.text
        logger.info(f"Исходный текст:\n{raw_text}")
        
        # Извлекаем участников
        new_members = extract_members(raw_text)
        logger.info(f"Извлеченные участники: {new_members}")
        
        if not new_members:
            error_msg = "⚠️ Не найден список пользователей. Ожидаю формат:\nАктуальные участники:\n@username1\n123456789"
            await update.message.reply_text(error_msg)
            return

        # Получаем текущих участников
        chat = await context.bot.get_chat(MAIN_CHAT_ID)
        try:
            admins = await chat.get_administrators()
            logger.info(f"Найдено {len(admins)} администраторов")
        except Exception as e:
            logger.error(f"Ошибка получения списка админов: {e}")
            await update.message.reply_text(f"❌ Ошибка доступа к чату {MAIN_CHAT_ID}")
            return

        current_members = {
            str(member.user.id) for member in admins
        }.union(
            {member.user.username.lower() for member in admins if member.user.username}
        )
        logger.info(f"Текущие участники: {current_members}")

        # Поиск кого удалять
        to_remove = [
            member for member in admins
            if (str(member.user.id) not in new_members) and 
               (member.user.username and member.user.username.lower() not in new_members)
        ]

        if not to_remove:
            logger.info("Нет пользователей для удаления")
            await update.message.reply_text("✅ Все пользователи в списке актуальны")
            return

        # Процесс удаления
        success = []
        failed = []
        
        for member in to_remove:
            try:
                if member.status != 'creator':
                    await context.bot.ban_chat_member(MAIN_CHAT_ID, member.user.id)
                    username = member.user.username or member.user.id
                    success.append(username)
                    logger.info(f"Успешно удален: {username}")
            except Exception as e:
                failed.append(str(member.user.id))
                logger.error(f"Ошибка удаления {member.user.id}: {e}")

        # Отчет о выполнении
        report = []
        if success:
            report.append(f"✅ Удалено: {', '.join(map(str, success))}")
        if failed:
            report.append(f"❌ Не удалось удалить: {', '.join(failed)}")
        
        if report:
            await update.message.reply_text("\n".join(report))

    except Exception as e:
        logger.exception("Критическая ошибка в check_members:")
        await update.message.reply_text(f"🚨 Произошла ошибка: {str(e)}")



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
