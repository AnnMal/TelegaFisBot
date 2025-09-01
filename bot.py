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

# Инициализация логов (ДВОЙНАЯ ПРОВЕРКА)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 1. Проверка: Функция post_init (часто отсутствует)
async def post_init(app: Application):
    """Отправляет уведомление о старте"""
    try:
        await app.bot.send_message(
            chat_id=LIST_CHAT_ID,
            text="🔄 Бот запущен и готов к работе!"
        )
        logger.info("Уведомление о старте отправлено")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")

# 2. Проверка: Улучшенный парсинг участников
def extract_members(text: str) -> set:
    """Извлекает user_id и @username с валидацией"""
    members = set()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    for line in lines:
        # Пропускаем заголовок
        if "актуальные участники" in line.lower():
            continue
            
        # Ищем ID (только цифры)
        if re.fullmatch(r'\d{5,}', line):
            members.add(line)
        # Ищем юзернеймы
        elif line.startswith('@'):
            username = line[1:].lower()
            if re.fullmatch(r'[a-z0-9_]{5,32}', username):
                members.add(username)
    
    logger.info(f"Извлечены участники: {members}")
    return members

# 3. Проверка: Обработчик сообщений с защитой от ошибок
async def check_members(update: Update, context: CallbackContext):
    """Основная логика проверки списка"""
    try:
        # Верификация чата
        if update.effective_chat.id != LIST_CHAT_ID:
            logger.warning(f"Игнорирую сообщение из чата {update.effective_chat.id}")
            return

        # Парсинг списка
        new_members = extract_members(update.message.text)
        if not new_members:
            await update.message.reply_text("❌ Не найден валидный список участников")
            return

        # Проверка прав бота
        bot_member = await context.bot.get_chat_member(MAIN_CHAT_ID, context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("⚠️ У меня нет прав на удаление!")
            return

        # Получение текущих участников
        admins = await context.bot.get_chat_administrators(MAIN_CHAT_ID)
        to_remove = []
        
        for member in admins:
            user_identifiers = {
                str(member.user.id),
                member.user.username.lower() if member.user.username else None
            }
            
            # Поиск отсутствующих в списке
            if not user_identifiers & new_members and member.status != "creator":
                to_remove.append(member)

        # Удаление участников
        for member in to_remove:
            try:
                await context.bot.ban_chat_member(
                    chat_id=MAIN_CHAT_ID,
                    user_id=member.user.id,
                    until_date=int(datetime.now().timestamp()) + 60  # Бан на 1 минуту
                )
                logger.info(f"Удален: {member.user.username or member.user.id}")
            except Exception as e:
                logger.error(f"Ошибка удаления: {e}")

        await update.message.reply_text(f"✅ Готово! Обработано {len(to_remove)} участников")

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла внутренняя ошибка")

# 4. Проверка: Тестовая команда для диагностики
async def test_command(update: Update, context: CallbackContext):
    """Ручной запуск проверки"""
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

def main():
    application = Application.builder() \
        .token(TOKEN) \
        .post_init(post_init) \
        .build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("test", test_command))  # Диагностика
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=LIST_CHAT_ID) & filters.TEXT,
        check_members
    ))

    # Запуск бота
    logger.info("🤖 Бот запускается...")
    application.run_polling()

if __name__ == "__main__":
    main()
