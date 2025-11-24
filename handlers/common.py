from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from database import Database
from config import BACK_BUTTON_TEXT

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    try:
        from subscription import subscription_manager
        sub = subscription_manager.get_subscription(user.id)
        is_premium = sub['is_premium']
        premium_text = f"⭐ Premium до: {sub['days_left']} дн." if is_premium else "⭐ Premium"
    except:
        premium_text = "⭐ Premium"
        is_premium = False
    
    keyboard = [
        [KeyboardButton("➕ Добавить расход"), KeyboardButton("💰 Добавить доход")],
        [KeyboardButton("📥 Массовое добавление"), KeyboardButton("🗑 Массовое удаление")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("📈 Диаграмма")],
        [KeyboardButton("💡 Умные советы"), KeyboardButton("🏆 Достижения")],
        [KeyboardButton("📊 Сравнить месяцы"), KeyboardButton("🔮 Прогноз")],
        [KeyboardButton("💰 Бюджеты"), KeyboardButton("🔍 Поиск")],
        [KeyboardButton("📝 Последние 3 дня")],
        [KeyboardButton("📤 Экспорт"), KeyboardButton("📄 Экспорт PDF")],
        [KeyboardButton("❌ Удалить расход"), KeyboardButton("✅ Удалить доход")]
    ]
    if is_premium:
        keyboard.append([KeyboardButton("🎯 Фильтры категорий"), KeyboardButton(premium_text)])
    else:
        keyboard.append([KeyboardButton(premium_text)])
    
    keyboard.append([KeyboardButton(BACK_BUTTON_TEXT)])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    premium_status = "✨ <b>Premium активен!</b>" if is_premium else "Получи <b>Premium</b> всего за 1 ⭐"
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу тебе вести учет твоих финансов.\n\n"
        f"{premium_status}\n\n"
        "🎯 <b>Premium возможности:</b>\n"
        "• ✏️ Редактирование бюджетов\n"
        "• 🎯 Фильтрация категорий\n"
        "• 📊 Точная аналитика и прогнозы\n\n"
        "📋 <b>Основные функции:</b>\n"
        "• Добавление расходов и доходов\n"
        "• Статистика и диаграммы\n"
        "• Экспорт в Excel и PDF\n"
        "• Поиск и массовые операции\n"
        "• Умные советы и достижения\n\n"
        "Выбери действие из меню ниже:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler
    context.user_data.clear()
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END