from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from database import Database
from config import BACK_BUTTON_TEXT

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    
    keyboard = [
        [KeyboardButton("➕ Добавить расход"), KeyboardButton("💰 Добавить доход")],
        [KeyboardButton("📥 Массовое добавление"), KeyboardButton("🗑 Массовое удаление")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("📈 Диаграмма")],
        [KeyboardButton("📝 Последние 3 дня"), KeyboardButton("🔍 Поиск")],
        [KeyboardButton("📤 Экспорт"), KeyboardButton("📄 Экспорт PDF")],
        [KeyboardButton("❌ Удалить расход"), KeyboardButton("✅ Удалить доход")],
        [KeyboardButton(BACK_BUTTON_TEXT)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу тебе вести учет твоих финансов.\n\n"
        "Доступные функции:\n"
        "• Добавление расходов и доходов\n"
        "• Просмотр статистики за разные периоды\n"
        "• Обычное и массовое добавление с указанием даты\n"
        "• Поиск, диаграммы и удаление (в т.ч. массовое)\n"
        "• Экспорт в Excel и PDF\n\n"
        "Если передумал — просто нажми кнопку «⬅️ Назад» или отправь /cancel.\n\n"
        "Выбери действие из меню:",
        reply_markup=reply_markup
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    context.user_data.clear()
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

