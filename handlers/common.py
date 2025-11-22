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
        [KeyboardButton("💡 Умные советы"), KeyboardButton("🏆 Достижения")],
        [KeyboardButton("📊 Сравнить месяцы"), KeyboardButton("🔮 Прогноз")],
        [KeyboardButton("💰 Бюджеты"), KeyboardButton("🔍 Поиск")],
        [KeyboardButton("📝 Последние 3 дня")],
        [KeyboardButton("📤 Экспорт"), KeyboardButton("📄 Экспорт PDF")],
        [KeyboardButton("❌ Удалить расход"), KeyboardButton("✅ Удалить доход")],
        [KeyboardButton(BACK_BUTTON_TEXT)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу тебе вести учет твоих финансов.\n\n"
        "🎯 <b>Новые возможности:</b>\n"
        "• 💡 Умные советы и аналитика\n"
        "• 🏆 Достижения и интересные факты\n"
        "• 💰 Бюджеты с автоуведомлениями\n"
        "• 📊 Сравнение периодов\n"
        "• 🔮 Прогноз расходов\n\n"
        "📋 <b>Основные функции:</b>\n"
        "• Добавление расходов и доходов\n"
        "• Статистика и диаграммы\n"
        "• Экспорт в Excel и PDF\n"
        "• Поиск и массовые операции\n\n"
        "Выбери действие из меню ниже:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    context.user_data.clear()
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

