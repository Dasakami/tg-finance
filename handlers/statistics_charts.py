"""
Обновленные обработчики для диаграмм с выбором типа и фильтрами
"""
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from database import Database
from charts_improved import create_statistics_chart
from handlers.common import cancel
from config import BACK_BUTTON_TEXT

db = Database()

WAITING_FOR_CHART_CATEGORIES = 300


async def show_chart_menu_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню выбора диаграммы"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Круговая", callback_data="chart_type_pie"),
            InlineKeyboardButton("📈 Столбчатая", callback_data="chart_type_bar")
        ],
        [
            InlineKeyboardButton("📉 Линейная", callback_data="chart_type_line")
        ],
        [
            InlineKeyboardButton("⚙️ С фильтрами (Premium)", callback_data="chart_with_filters")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📈 <b>Выбери тип диаграммы:</b>\n\n"
        "📊 <b>Круговая</b> - проценты по категориям\n"
        "📈 <b>Столбчатая</b> - сравнение сумм\n"
        "📉 <b>Линейная</b> - динамика расходов/доходов\n\n"
        "⚙️ <b>С фильтрами</b> - исключи ненужные категории",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def chart_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбран тип диаграммы"""
    await update.callback_query.answer()
    
    chart_type = update.callback_query.data.replace("chart_type_", "")
    context.user_data['chart_type'] = chart_type
    
    keyboard = [
        [
            InlineKeyboardButton("30 дней", callback_data="chart_period_30"),
            InlineKeyboardButton("90 дней", callback_data="chart_period_90")
        ],
        [
            InlineKeyboardButton("Все время", callback_data="chart_period_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    chart_names = {
        'pie': 'Круговая',
        'bar': 'Столбчатая',
        'line': 'Линейная'
    }
    
    await update.callback_query.edit_message_text(
        f"📊 {chart_names.get(chart_type, 'Диаграмма')}\n\n"
        "Выбери период:",
        reply_markup=reply_markup
    )


async def chart_period_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбран период диаграммы"""
    await update.callback_query.answer("Генерирую диаграмму...")
    
    period_str = update.callback_query.data.replace("chart_period_", "")
    days = None if period_str == "all" else int(period_str)
    
    chart_type = context.user_data.get('chart_type', 'pie')
    user_id = update.effective_user.id
    
    stats = db.get_statistics(user_id, days)
    
    period_text = {
        30: "30 дней",
        90: "90 дней",
        None: "все время"
    }.get(days, f"{days} дней")

    chart_path = create_statistics_chart(
        stats, 
        period_text, 
        chart_type=chart_type,
        excluded_categories=None
    )
    
    if not chart_path or not os.path.exists(chart_path):
        await update.callback_query.edit_message_text(
            "Недостаточно данных для построения диаграммы."
        )
        context.user_data.clear()
        return
    
    try:
        await update.callback_query.message.reply_photo(
            photo=open(chart_path, 'rb'),
            caption=f"📈 Диаграмма за {period_text}"
        )
        await update.callback_query.message.delete()
    finally:
        if os.path.exists(chart_path):
            os.remove(chart_path)
        context.user_data.clear()


async def chart_with_filters_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания диаграммы с фильтрами (Premium)"""
    await update.callback_query.answer()
    user_id = update.effective_user.id
    
    try:
        from subscription import subscription_manager
        if not subscription_manager.is_premium(user_id):
            keyboard = [[InlineKeyboardButton("⭐ Получить Premium", callback_data="show_premium")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                "🔒 <b>Premium функция</b>\n\n"
                "Диаграммы с фильтрами доступны только для Premium подписчиков.\n\n"
                "💎 Получи Premium всего за 1 ⭐ на месяц!",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return
    except ImportError:
        pass
    
    stats = db.get_statistics(user_id, 90)
    categories = list(stats['expenses_by_category'].keys())
    
    if not categories:
        await update.callback_query.edit_message_text(
            "У тебя пока нет категорий расходов."
        )
        return
    
    context.user_data['excluded_categories'] = []
    
    keyboard = []
    for cat in categories[:15]:  
        keyboard.append([
            InlineKeyboardButton(
                f"☑️ {cat}",
                callback_data=f"chart_toggle_{cat}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Готово", callback_data="chart_filters_done"),
        InlineKeyboardButton("❌ Отмена", callback_data="chart_filters_cancel")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "🎯 <b>Выбери категории для ИСКЛЮЧЕНИЯ</b>\n\n"
        "Нажми на категорию чтобы исключить её из диаграммы.\n"
        "☑️ - включена\n"
        "⬜ - исключена\n\n"
        "Когда закончишь, нажми «Готово».",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return WAITING_FOR_CHART_CATEGORIES


async def chart_toggle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить категорию"""
    await update.callback_query.answer()
    
    category = update.callback_query.data.replace("chart_toggle_", "")
    excluded = context.user_data.get('excluded_categories', [])
    
    if category in excluded:
        excluded.remove(category)
    else:
        excluded.append(category)
    
    context.user_data['excluded_categories'] = excluded
    
    user_id = update.effective_user.id
    stats = db.get_statistics(user_id, 90)
    categories = list(stats['expenses_by_category'].keys())
    
    keyboard = []
    for cat in categories[:15]:
        icon = "⬜" if cat in excluded else "☑️"
        keyboard.append([
            InlineKeyboardButton(
                f"{icon} {cat}",
                callback_data=f"chart_toggle_{cat}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Готово", callback_data="chart_filters_done"),
        InlineKeyboardButton("❌ Отмена", callback_data="chart_filters_cancel")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    excluded_text = f"\n\n🚫 Исключено: {', '.join(excluded)}" if excluded else ""
    
    await update.callback_query.edit_message_text(
        f"🎯 <b>Выбери категории для ИСКЛЮЧЕНИЯ</b>\n\n"
        "☑️ - включена\n"
        "⬜ - исключена" + excluded_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def chart_filters_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фильтры выбраны, создаем диаграмму"""
    await update.callback_query.answer()
    
    excluded = context.user_data.get('excluded_categories', [])
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Круговая", callback_data="chart_filtered_pie"),
            InlineKeyboardButton("📈 Столбчатая", callback_data="chart_filtered_bar")
        ],
        [
            InlineKeyboardButton("📉 Линейная", callback_data="chart_filtered_line")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    excluded_text = f"🚫 Исключено: {', '.join(excluded)}\n\n" if excluded else ""
    
    await update.callback_query.edit_message_text(
        f"{excluded_text}Выбери тип диаграммы:",
        reply_markup=reply_markup
    )


async def chart_filtered_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбран тип для фильтрованной диаграммы"""
    await update.callback_query.answer("Генерирую диаграмму...")
    
    chart_type = update.callback_query.data.replace("chart_filtered_", "")
    excluded = context.user_data.get('excluded_categories', [])
    user_id = update.effective_user.id

    stats = db.get_statistics(user_id, 30)
    
    chart_path = create_statistics_chart(
        stats,
        "30 дней",
        chart_type=chart_type,
        excluded_categories=excluded
    )
    
    if not chart_path or not os.path.exists(chart_path):
        await update.callback_query.edit_message_text(
            "Недостаточно данных для построения диаграммы."
        )
        context.user_data.clear()
        return
    
    try:
        caption = "📈 Диаграмма за 30 дней"
        if excluded:
            caption += f"\n🚫 Исключено категорий: {len(excluded)}"
        
        await update.callback_query.message.reply_photo(
            photo=open(chart_path, 'rb'),
            caption=caption
        )
        await update.callback_query.message.delete()
    finally:
        if os.path.exists(chart_path):
            os.remove(chart_path)
        context.user_data.clear()


async def chart_filters_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена фильтров"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Отменено.")
    context.user_data.clear()
    return ConversationHandler.END


chart_filters_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(chart_with_filters_start, pattern="^chart_with_filters$")],
    states={
        WAITING_FOR_CHART_CATEGORIES: [
            CallbackQueryHandler(chart_toggle_category, pattern="^chart_toggle_"),
            CallbackQueryHandler(chart_filters_done, pattern="^chart_filters_done$"),
            CallbackQueryHandler(chart_filters_cancel, pattern="^chart_filters_cancel$"),
        ]
    },
    fallbacks=[
        CallbackQueryHandler(chart_filters_cancel, pattern="^chart_filters_cancel$")
    ]
)


__all__ = [
    'show_chart_menu_new',
    'chart_type_selected',
    'chart_period_selected',
    'chart_filters_conversation',
    'chart_filtered_type_selected'
]