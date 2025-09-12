import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Настройки
TOKEN = "8285946823:AAE6mT6BtJsOkTQFsP-IrBHonhtaUaJAg8g"
MAIN_CHAT_ID = -4884863804  # Чат, откуда будем удалять
LIST_CHAT_ID = -1002900105796  # Чат с актуальными участниками

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def handle_list(update: Update, context: CallbackContext):
    """Обработка сообщения со списком участников и удаление лишних"""
    try:
        # Проверяем, что сообщение из нужного чата
        if update.effective_chat.id != LIST_CHAT_ID:
            return

        text = update.message.text
        
        # Проверяем формат сообщения
        if not text.startswith("Актуальные участники:"):
            await update.message.reply_text("❌ Неверный формат. Начните сообщение с 'Актуальные участники:'")
            return

        # Получаем список актуальных участников
        lines = text.split('\n')
        actual_members = set()
        
        for line in lines[1:]:  # Пропускаем первую строку
            line = line.strip()
            if line:  # Если строка не пустая
                actual_members.add(line.lower())  # Приводим к нижнему регистру

        # Получаем текущих администраторов основного чата
        chat_members = await context.bot.get_chat_administrators(MAIN_CHAT_ID)
        removed = []
        errors = []

        for member in chat_members:
            # Пропускаем создателя чата и самого бота
            if member.status == 'creator' or member.user.is_bot:
                continue

            # Формируем идентификаторы пользователя для проверки
            user_identifiers = [str(member.user.id)]
            if member.user.username:
                user_identifiers.append(f"@{member.user.username.lower()}")
            
            # Проверяем, есть ли пользователь в актуальном списке
            if not any(ident in actual_members for ident in user_identifiers):
                try:
                    await context.bot.ban_chat_member(
                        chat_id=MAIN_CHAT_ID,
                        user_id=member.user.id
                    )
                    username = f"@{member.user.username}" if member.user.username else str(member.user.id)
                    removed.append(username)
                    logger.info(f"Удалён участник: {username}")
                except Exception as e:
                    errors.append(str(member.user.id))
                    logger.error(f"Ошибка удаления {member.user.id}: {e}")

        # Формируем отчёт
        report = []
        if removed:
            report.append(f"✅ Удалено: {len(removed)}")
            report.append(", ".join(removed))
        else:
            report.append("🤷 Нет пользователей для удаления")
        
        if errors:
            report.append(f"❌ Ошибок: {len(errors)}")

        await update.message.reply_text("\n".join(report))

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка при обработке")

async def start(update: Update, context: CallbackContext):
    """Обработка команды /start"""
    await update.message.reply_text(
        "🤖 Бот для управления участниками чата\n"
        "Отправьте список в формате:\n\n"
        "Актуальные участники:\n"
        "@username1\n"
        "123456789\n"
        "@username2"
    )

async def check_rights(update: Update, context: CallbackContext):
    """Проверка прав бота в целевом чате"""
    try:
        chat = await context.bot.get_chat(MAIN_CHAT_ID)
        bot_member = await chat.get_member(context.bot.id)
        
        if bot_member.can_restrict_members:
            await update.message.reply_text("🛡️ Бот имеет права на удаление участников")
        else:
            await update.message.reply_text("⛔ Бот НЕ имеет прав на удаление участников!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка проверки прав: {e}")

def main():
    """Запуск бота"""
    app = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rights", check_rights))
    
    # Основной обработчик сообщений
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=LIST_CHAT_ID) & filters.TEXT,
            handle_list
        )
    )
    
    logger.info("Бот запущен и готов к работе...")
    app.run_polling()

if __name__ == "__main__":
    main()
