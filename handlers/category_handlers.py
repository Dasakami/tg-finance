"""
Обработчики для управления категориями и просмотра трат по категориям
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CommandHandler, CallbackQueryHandler, filters
)
from database import Database
from custom_categories import category_manager
from utils import format_currency, format_date
from handlers.common import cancel
from config import BACK_BUTTON_TEXT

db = Database()

WAITING_FOR_CATEGORY_NAME = 500
WAITING_FOR_CATEGORY_ICON = 501


async def show_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню управления категориями"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить категорию расходов", callback_data="cat_add_expense")],
        [InlineKeyboardButton("➕ Добавить источник доходов", callback_data="cat_add_income")],
        [InlineKeyboardButton("📋 Мои категории расходов", callback_data="cat_list_expense")],
        [InlineKeyboardButton("📋 Мои источники доходов", callback_data="cat_list_income")],
        [InlineKeyboardButton("🗑 Удалить категорию", callback_data="cat_delete_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📂 <b>Управление категориями</b>\n\n"
        "Создавай свои категории для быстрого добавления операций!",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать добавление категории"""
    await update.callback_query.answer()
    
    category_type = 'expense' if 'expense' in update.callback_query.data else 'income'
    context.user_data['new_category_type'] = category_type
    
    type_name = "расхода" if category_type == 'expense' else "дохода"
    
    await update.callback_query.edit_message_text(
        f"Введи название категории {type_name}:\n\n"
        "Например: Общага, Подработка, Кафе..."
    )
    
    return WAITING_FOR_CATEGORY_NAME


async def category_name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия категории"""
    category_name = update.message.text.strip()
    context.user_data['new_category_name'] = category_name
    
    keyboard = [
        [
            InlineKeyboardButton("🍔", callback_data="icon_🍔"),
            InlineKeyboardButton("🏠", callback_data="icon_🏠"),
            InlineKeyboardButton("🚗", callback_data="icon_🚗"),
            InlineKeyboardButton("💊", callback_data="icon_💊")
        ],
        [
            InlineKeyboardButton("🎮", callback_data="icon_🎮"),
            InlineKeyboardButton("👕", callback_data="icon_👕"),
            InlineKeyboardButton("📚", callback_data="icon_📚"),
            InlineKeyboardButton("🎬", callback_data="icon_🎬")
        ],
        [
            InlineKeyboardButton("💼", callback_data="icon_💼"),
            InlineKeyboardButton("💻", callback_data="icon_💻"),
            InlineKeyboardButton("🎁", callback_data="icon_🎁"),
            InlineKeyboardButton("✨", callback_data="icon_✨")
        ],
        [InlineKeyboardButton("⏭ Без иконки", callback_data="icon_none")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Название: {category_name}\n\n"
        "Выбери иконку или пропусти:",
        reply_markup=reply_markup
    )
    
    return WAITING_FOR_CATEGORY_ICON


async def category_icon_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора иконки"""
    await update.callback_query.answer()
    
    user_id = update.effective_user.id
    category_name = context.user_data['new_category_name']
    category_type = context.user_data['new_category_type']
    
    icon_data = update.callback_query.data.replace("icon_", "")
    icon = None if icon_data == "none" else icon_data
    
    success = category_manager.add_category(user_id, category_name, category_type, icon)
    
    if success:
        display_name = f"{icon} {category_name}" if icon else category_name
        type_name = "расхода" if category_type == 'expense' else "дохода"
        
        await update.callback_query.edit_message_text(
            f"✅ Категория {type_name} добавлена:\n{display_name}"
        )
    else:
        await update.callback_query.edit_message_text(
            "❌ Такая категория уже существует!"
        )
    
    context.user_data.clear()
    return ConversationHandler.END


async def list_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список категорий"""
    await update.callback_query.answer()
    
    category_type = 'expense' if 'expense' in update.callback_query.data else 'income'
    user_id = update.effective_user.id
    
    categories = category_manager.get_categories(user_id, category_type)
    
    type_name = "расходов" if category_type == 'expense' else "доходов"
    message = f"📋 <b>Категории {type_name}</b>\n\n"
    
    custom_found = False
    for cat in categories:
        if cat['is_custom']:
            if not custom_found:
                message += "<b>Твои категории:</b>\n"
                custom_found = True
            fav = "⭐ " if cat['is_favorite'] else ""
            message += f"  {fav}{cat['name']}\n"
    
    if custom_found:
        message += "\n"
    
    message += "<b>Стандартные категории:</b>\n"
    for cat in categories:
        if not cat['is_custom']:
            message += f"  {cat['name']}\n"
    
    await update.callback_query.edit_message_text(message, parse_mode='HTML')


async def delete_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню удаления категорий"""
    await update.callback_query.answer()
    
    user_id = update.effective_user.id
    
    expense_cats = [c for c in category_manager.get_categories(user_id, 'expense') if c['is_custom']]
    income_cats = [c for c in category_manager.get_categories(user_id, 'income') if c['is_custom']]
    
    if not expense_cats and not income_cats:
        await update.callback_query.edit_message_text(
            "У тебя нет пользовательских категорий для удаления."
        )
        return
    
    keyboard = []
    
    if expense_cats:
        for cat in expense_cats[:10]:
            keyboard.append([InlineKeyboardButton(
                f"🗑 {cat['name']} (расход)",
                callback_data=f"del_cat_expense_{cat['name'].split(' ', 1)[-1]}"
            )])
    
    if income_cats:
        for cat in income_cats[:10]:
            keyboard.append([InlineKeyboardButton(
                f"🗑 {cat['name']} (доход)",
                callback_data=f"del_cat_income_{cat['name'].split(' ', 1)[-1]}"
            )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "🗑 <b>Удаление категории</b>\n\n"
        "Выбери категорию для удаления:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def delete_category_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления категории"""
    await update.callback_query.answer()
    
    data = update.callback_query.data.replace("del_cat_", "")
    parts = data.split("_", 1)
    category_type = parts[0]
    category_name = parts[1]
    
    user_id = update.effective_user.id
    success = category_manager.delete_category(user_id, category_name, category_type)
    
    if success:
        await update.callback_query.edit_message_text(
            f"✅ Категория '{category_name}' удалена."
        )
    else:
        await update.callback_query.edit_message_text(
            "❌ Не удалось удалить категорию."
        )


async def view_expenses_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню просмотра трат по категориям"""
    user_id = update.effective_user.id
    stats = db.get_statistics(user_id, 90)
    
    categories = list(stats['expenses_by_category'].keys())
    
    if not categories:
        await update.message.reply_text("У тебя пока нет расходов по категориям.")
        return
    
    keyboard = []
    for cat in categories[:15]:
        amount = stats['expenses_by_category'][cat]
        keyboard.append([InlineKeyboardButton(
            f"{cat} ({format_currency(amount)} руб.)",
            callback_data=f"view_cat_{cat}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📂 <b>Выбери категорию</b>\n\n"
        "Посмотри детальную статистику по категории:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def category_selected_for_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Категория выбрана для просмотра"""
    await update.callback_query.answer()
    
    category = update.callback_query.data.replace("view_cat_", "")
    context.user_data['view_category'] = category
    
    keyboard = [
        [
            InlineKeyboardButton("Вчера", callback_data="cat_period_1"),
            InlineKeyboardButton("3 дня", callback_data="cat_period_3")
        ],
        [
            InlineKeyboardButton("7 дней", callback_data="cat_period_7"),
            InlineKeyboardButton("30 дней", callback_data="cat_period_30")
        ],
        [
            InlineKeyboardButton("90 дней", callback_data="cat_period_90"),
            InlineKeyboardButton("Все время", callback_data="cat_period_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        f"📂 Категория: <b>{category}</b>\n\n"
        "Выбери период:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def show_category_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали по категории"""
    await update.callback_query.answer()
    
    category = context.user_data.get('view_category')
    period_str = update.callback_query.data.replace("cat_period_", "")
    days = None if period_str == "all" else int(period_str)
    
    user_id = update.effective_user.id
    expenses = db.get_expenses(user_id, days)
    
    category_expenses = [e for e in expenses if e['category'] == category]
    
    if not category_expenses:
        await update.callback_query.edit_message_text(
            f"В категории '{category}' нет расходов за выбранный период."
        )
        context.user_data.clear()
        return
    
    total = sum(e['amount'] for e in category_expenses)
    count = len(category_expenses)
    avg = total / count if count > 0 else 0
    
    period_text = {
        1: "вчера",
        3: "за 3 дня",
        7: "за 7 дней",
        30: "за 30 дней",
        90: "за 90 дней",
        None: "за все время"
    }.get(days, f"за {days} дней")
    
    message = f"📂 <b>{category}</b> {period_text}\n\n"
    message += f"💸 Всего потрачено: {format_currency(total)} руб.\n"
    message += f"📊 Операций: {count}\n"
    message += f"📈 Средний чек: {format_currency(avg)} руб.\n\n"
    message += "<b>Последние траты:</b>\n\n"
    
    for exp in category_expenses[:10]:
        date_str = format_date(exp['date'].isoformat() if hasattr(exp['date'], 'isoformat') else str(exp['date']))
        desc = f" - {exp['description']}" if exp.get('description') else ""
        message += f"• {format_currency(exp['amount'])} руб.{desc}\n"
        message += f"  📅 {date_str}\n\n"
    
    if len(category_expenses) > 10:
        message += f"...и ещё {len(category_expenses) - 10} операций"
    
    await update.callback_query.edit_message_text(message, parse_mode='HTML')
    context.user_data.clear()


add_category_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(add_category_start, pattern="^cat_add_(expense|income)$")
    ],
    states={
        WAITING_FOR_CATEGORY_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, category_name_entered)
        ],
        WAITING_FOR_CATEGORY_ICON: [
            CallbackQueryHandler(category_icon_selected, pattern="^icon_")
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)


__all__ = [
    'show_category_menu',
    'list_categories',
    'delete_category_menu',
    'delete_category_confirm',
    'view_expenses_by_category',
    'category_selected_for_view',
    'show_category_details',
    'add_category_conversation'
]