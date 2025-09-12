import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройки
TOKEN = "8285946823:AAE6mT6BtJsOkTQFsP-IrBHonhtaUaJAg8g"
MAIN_CHAT_ID = -4884863804    # Чат для очистки
LIST_CHAT_ID = -1002900105796 # Чат для команд

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

current_members = set()  # Храним текущий список участников

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок"""
    logger.error("Ошибка в обработчике", exc_info=context.error)
    if isinstance(update, Update):
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")

async def set_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка списка участников через команду"""
    try:
        global current_members
        
        # Проверка чата
        if update.message.chat.id != LIST_CHAT_ID:
            await update.message.reply_text("❌ Команда доступна только в специальном чате")
            return
            
        # Проверка аргументов
        if not context.args:
            await update.message.reply_text(
                "ℹ️ Использование команды:\n\n"
                "/setmembers user1 user2 user3\n\n"
                "Где user может быть:\n"
                "- @username (например @john)\n"
                "- user_id (например 123456789)\n\n"
                "Пример:\n"
                "/setmembers @john 123456789 @alice"
            )
            return
            
        # Обработка списка
        new_members = set()
        invalid_members = []
        
        for arg in context.args:
            arg = arg.strip().lower()
            
            # Обработка username (@username)
            if arg.startswith('@'):
                username = arg[1:]
                if len(username) >= 5 and username.replace('_', '').isalnum():
                    new_members.add(f"@{username}")
                else:
                    invalid_members.append(arg)
            
            # Обработка user_id (цифры)
            elif arg.isdigit() and len(arg) >= 5:
                new_members.add(arg)
            
            else:
                invalid_members.append(arg)
        
        # Сохраняем новый список
        current_members = new_members
        
        # Формируем отчет
        response = [
            f"✅ Установлен новый список ({len(current_members)} участников):"
        ]
        
        # Добавляем username с @ и ID без изменений
        response.extend(sorted(f"• {m}" for m in current_members))
        
        if invalid_members:
            response.append("\n❌ Некорректные значения:")
            response.extend(f"× {m}" for m in invalid_members)
        
        await update.message.reply_text("\n".join(response))
        
    except Exception as e:
        logger.error(f"Ошибка в set_members: {e}")
        await update.message.reply_text("❌ Ошибка обработки списка")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    help_text = (
        "🤖 Бот управления участниками чатов\n\n"
        "🔹 Основные команды:\n"
        "/start - показать это сообщение\n"
        "/setmembers - задать список участников\n"
        "/showmembers - показать текущий список\n\n"
        "📝 Формат списка:\n"
        "/setmembers @username1 @username2 123456789\n\n"
        "⚠️ Все команды работают только в специальном чате"
    )
    await update.message.reply_text(help_text)

async def show_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущий список участников"""
    try:
        if not current_members:
            await update.message.reply_text("📭 Список участников пуст")
            return
            
        response = [
            "📋 Текущий список участников:",
            *sorted(f"• {m}" for m in current_members),
            f"\nВсего: {len(current_members)}"
        ]
        
        await update.message.reply_text("\n".join(response))
        
    except Exception as e:
        logger.error(f"Ошибка в show_members: {e}")
        await update.message.reply_text("❌ Ошибка отображения списка")

def main():
    """Запуск бота"""
    app = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setmembers", set_members))
    app.add_handler(CommandHandler("showmembers", show_members))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    logger.info("Бот успешно запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
