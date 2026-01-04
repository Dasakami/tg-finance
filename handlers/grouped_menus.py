"""
Сгруппированные меню для удобной навигации
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from balance import balance_manager
from utils import format_currency


# ============= 📊 СТАТИСТИКА =============

async def show_statistics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Единое меню статистики"""
    keyboard = [
        [InlineKeyboardButton("📊 Вчера", callback_data="stat_1"),
         InlineKeyboardButton("📊 3 дня", callback_data="stat_3")],
        [InlineKeyboardButton("📊 7 дней", callback_data="stat_7"),
         InlineKeyboardButton("📊 30 дней", callback_data="stat_30")],
        [InlineKeyboardButton("📊 90 дней", callback_data="stat_90"),
         InlineKeyboardButton("📊 Всё время", callback_data="stat_all")],
        [InlineKeyboardButton("━━━━━━━━━━━━", callback_data="divider")],
        [InlineKeyboardButton("📝 Последние 3 дня", callback_data="last_3_days"),
         InlineKeyboardButton("📝 Последние 7 дней", callback_data="last_7_days")],
        [InlineKeyboardButton("📊 Детали по категориям", callback_data="category_details")],
        [InlineKeyboardButton("📊 Сравнить месяцы", callback_data="compare_months")],
        [InlineKeyboardButton("📤 Экспорт Excel", callback_data="export_menu"),
         InlineKeyboardButton("📄 Экспорт PDF", callback_data="pdf_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📊 <b>Статистика и отчёты</b>\n\n"
        "Выбери что хочешь посмотреть:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


# ============= 📈 ДИАГРАММЫ =============

async def show_charts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Единое меню диаграмм"""
    keyboard = [
        [InlineKeyboardButton("💸 Расходы", callback_data="chart_expenses"),
         InlineKeyboardButton("💰 Доходы", callback_data="chart_income")],
        [InlineKeyboardButton("📊 Расходы + Доходы", callback_data="chart_both")],
        [InlineKeyboardButton("━━━━━━━━━━━━", callback_data="divider")],
        [InlineKeyboardButton("📂 По категориям", callback_data="chart_categories")],
        [InlineKeyboardButton("📈 Сравнение месяцев", callback_data="chart_compare")]
    ]
    
    # Premium функция - фильтры
    try:
        from subscription import subscription_manager
        user_id = update.effective_user.id
        if subscription_manager.is_premium(user_id):
            keyboard.append([InlineKeyboardButton(
                "🎯 С фильтрами (Premium)",
                callback_data="chart_with_filters"
            )])
    except:
        pass
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📈 <b>Диаграммы и визуализация</b>\n\n"
        "Выбери тип диаграммы:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


# ============= 🎯 УМНОЕ =============

async def show_smart_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню умных функций"""
    keyboard = [
        [InlineKeyboardButton("💡 Умные советы", callback_data="smart_tips"),
         InlineKeyboardButton("🏆 Достижения", callback_data="achievements")],
        [InlineKeyboardButton("🔮 Прогноз расходов", callback_data="forecast"),
         InlineKeyboardButton("📊 Сравнить периоды", callback_data="compare_periods")],
        [InlineKeyboardButton("━━━━━━━━━━━━", callback_data="divider")],
        [InlineKeyboardButton("🔔 Уведомления", callback_data="notifications"),
         InlineKeyboardButton("⏰ Регулярные траты", callback_data="regular_expenses")],
        [InlineKeyboardButton("📊 Сравнение категорий", callback_data="category_comparison")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎯 <b>Умные функции</b>\n\n"
        "Анализ, советы и прогнозы:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


# ============= 🔧 ИНСТРУМЕНТЫ =============

async def show_tools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню инструментов"""
    keyboard = [
        [InlineKeyboardButton("📥 Массовое добавление", callback_data="bulk_add"),
         InlineKeyboardButton("🗑 Массовое удаление", callback_data="bulk_delete")],
        [InlineKeyboardButton("❌ Удалить расход", callback_data="delete_expense"),
         InlineKeyboardButton("✅ Удалить доход", callback_data="delete_income")],
        [InlineKeyboardButton("━━━━━━━━━━━━", callback_data="divider")],
        [InlineKeyboardButton("📤 Экспорт в Excel", callback_data="export_excel"),
         InlineKeyboardButton("📄 Экспорт в PDF", callback_data="export_pdf")],
        [InlineKeyboardButton("🔄 Пересчитать баланс", callback_data="recalc_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user_id = update.effective_user.id
    balance = balance_manager.get_balance(user_id)
    
    await update.message.reply_text(
        f"🔧 <b>Инструменты</b>\n\n"
        f"Текущий баланс: {format_currency(balance['total_balance'])} сом\n\n"
        "Выбери инструмент:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


# ============= 💰 МОЙ БАЛАНС =============

async def show_balance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Расширенное меню баланса"""
    user_id = update.effective_user.id
    balance = balance_manager.get_balance(user_id)
    
    # Получаем статистику
    from database import Database
    db = Database()
    stats = db.get_statistics(user_id, 30)
    
    message = "💰 <b>Мой баланс</b>\n\n"
    message += f"💵 Основной: {format_currency(balance['balance'])} сом\n"
    message += f"🔒 Скрытый: {format_currency(balance['hidden_balance'])} сом\n"
    message += f"━━━━━━━━━━━━━━━━\n"
    message += f"📊 <b>Всего: {format_currency(balance['total_balance'])} сом</b>\n\n"
    
    message += "<b>За последние 30 дней:</b>\n"
    message += f"💰 Доходы: {format_currency(stats['total_income'])} сом\n"
    message += f"💸 Расходы: {format_currency(stats['total_expenses'])} сом\n"
    message += f"💵 Изменение: {format_currency(stats['balance'])} сом\n\n"
    
    message += "💡 <i>Скрытый баланс - это твои отложенные деньги</i>"
    
    keyboard = [
        [InlineKeyboardButton("➕ В скрытое", callback_data="hidden_add"),
         InlineKeyboardButton("➖ Из скрытого", callback_data="hidden_remove")],
        [InlineKeyboardButton("📜 История операций", callback_data="hidden_history")],
        [InlineKeyboardButton("🔄 Пересчитать баланс", callback_data="balance_recalc")],
        [InlineKeyboardButton("📊 Детальная статистика", callback_data="stat_30")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


# ============= 📂 МОИ КАТЕГОРИИ =============

async def show_categories_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Расширенное меню категорий"""
    user_id = update.effective_user.id
    
    from custom_categories import category_manager
    
    expense_cats = category_manager.get_categories(user_id, 'expense')
    income_cats = category_manager.get_categories(user_id, 'income')
    
    custom_expense = len([c for c in expense_cats if c['is_custom']])
    custom_income = len([c for c in income_cats if c['is_custom']])
    
    message = "📂 <b>Мои категории</b>\n\n"
    message += f"📊 Категорий расходов: {len(expense_cats)} (твоих: {custom_expense})\n"
    message += f"💰 Источников доходов: {len(income_cats)} (твоих: {custom_income})\n\n"
    message += "💡 Создавай свои категории для быстрого добавления операций!"
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить категорию расхода", callback_data="cat_add_expense")],
        [InlineKeyboardButton("➕ Добавить источник дохода", callback_data="cat_add_income")],
        [InlineKeyboardButton("━━━━━━━━━━━━", callback_data="divider")],
        [InlineKeyboardButton("📋 Мои категории расходов", callback_data="cat_list_expense")],
        [InlineKeyboardButton("📋 Мои источники доходов", callback_data="cat_list_income")],
        [InlineKeyboardButton("━━━━━━━━━━━━", callback_data="divider")],
        [InlineKeyboardButton("📊 Траты по категориям", callback_data="category_details")],
        [InlineKeyboardButton("🗑 Удалить категорию", callback_data="cat_delete_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


# ============= ОБРАБОТЧИКИ CALLBACK =============

async def handle_grouped_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общий обработчик для сгруппированных меню"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Игнорируем разделитель
    if data == "divider":
        return
    
    # Перенаправляем на соответствующие обработчики
    if data == "category_details":
        from handlers.category_handlers import view_expenses_by_category
        # Симулируем обычное сообщение
        update.message = query.message
        await view_expenses_by_category(update, context)
    
    elif data == "last_3_days":
        from handlers.statistics import show_last_3_days
        update.message = query.message
        await show_last_3_days(update, context)
    
    elif data == "last_7_days":
        from handlers.enhanced_statistics import show_last_7_days
        update.message = query.message
        await show_last_7_days(update, context)
    
    elif data == "compare_months":
        from handlers.smart_features import show_period_comparison
        update.message = query.message
        await show_period_comparison(update, context)
    
    elif data == "export_menu":
        from handlers.statistics import show_export_menu
        update.message = query.message
        await show_export_menu(update, context)
    
    elif data == "pdf_menu":
        from handlers.statistics import show_pdf_export_menu
        update.message = query.message
        await show_pdf_export_menu(update, context)
    
    # Остальные обработчики...


__all__ = [
    'show_statistics_menu',
    'show_charts_menu',
    'show_smart_menu',
    'show_tools_menu',
    'show_balance_menu',
    'show_categories_menu',
    'handle_grouped_callback'
]