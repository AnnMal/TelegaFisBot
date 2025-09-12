import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Настройки
TOKEN = "8285946823:AAE6mT6BtJsOkTQFsP-IrBHonhtaUaJAg8g"
MAIN_CHAT_ID = -4884863804    # Чат для очистки
LIST_CHAT_ID = -1002900105796 # Чат, где публикуются списки

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def handle_list_message(update: Update, context: CallbackContext):
    """Обработчик сообщений со списком участников"""
    try:
        logger.info(f"Получено сообщение: {update.message.text[:100]}...")
        
        if not update.message.text.startswith("Актуальные участники:"):
            await update.message.reply_text("ℹ️ Формат: 'Актуальные участники:' затем список")
            return
            
        # Извлекаем участников из списка
        members = [line.strip().lower() for line in update.message.text.split('\n')[1:] if line.strip()]
        await update.message.reply_text(f"✅ Получен список из {len(members)} участников")
        
        # Здесь будет логика удаления (можно добавить позже)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Ошибка обработки")

async def show_members(update: Update, context: CallbackContext):
    """Новая команда /members - показывает текущих администраторов"""
    try:
        admins = await update.effective_chat.get_administrators()
        admin_list = []
        
        for admin in admins:
            user = admin.user
            admin_info = f"👤 {user.full_name}"
            if user.username:
                admin_info += f" (@{user.username})"
            admin_info += f" [ID: {user.id}]"
            if admin.status == 'creator':
                admin_info += " - создатель"
            admin_list.append(admin_info)
        
        response = "📋 Текущие администраторы:\n\n" + "\n".join(admin_list)
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Ошибка команды /members: {e}")
        await update.message.reply_text("⚠️ Не удалось получить список администраторов")

async def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    help_text = (
        "🤖 Бот для управления участниками чата\n\n"
        "Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/members - список администраторов\n\n"
        "Отправьте список участников в формате:\n"
        "Актуальные участники:\n"
        "@username1\n"
        "123456789"
    )
    await update.message.reply_text(help_text)

def main():
    """Запуск бота"""
    app = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("members", show_members))
    
    # Обработчик списков участников
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=LIST_CHAT_ID) & filters.TEXT & ~filters.COMMAND,
            handle_list_message
        )
    )
    
    # Логирование всех входящих сообщений
    app.add_handler(
        MessageHandler(
            filters.ALL, 
            lambda u,c: logger.info(f"Входящее сообщение в чате {u.effective_chat.id}: {u.message.text if u.message else 'NO TEXT'}")
        ),
        group=-1
    )
    
    logger.info("Бот запущен и готов к работе...")
    app.run_polling()

if __name__ == "__main__":
    main()
