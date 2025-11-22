from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)
from database import Database
from utils import format_currency, format_date, parse_user_date
from handlers.common import cancel
from config import (
    WAITING_FOR_AMOUNT,
    WAITING_FOR_CATEGORY,
    WAITING_FOR_DESCRIPTION,
    WAITING_FOR_EXPENSE_DATE,
    BACK_BUTTON_TEXT
)

db = Database()

# Константы для пагинации
ITEMS_PER_PAGE = 5


async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи сумму расхода (например: 1500 или 99.50):")
    return WAITING_FOR_AMOUNT


async def add_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(',', '.'))
        if amount <= 0:
            await update.message.reply_text("Сумма должна быть положительным числом. Попробуй еще раз:")
            return WAITING_FOR_AMOUNT
        
        context.user_data['expense_amount'] = amount
        
        keyboard = [
            [
                InlineKeyboardButton("🍔 Еда", callback_data="cat_Еда"),
                InlineKeyboardButton("🚗 Транспорт", callback_data="cat_Транспорт")
            ],
            [
                InlineKeyboardButton("🛒 Покупки", callback_data="cat_Покупки"),
                InlineKeyboardButton("💊 Здоровье", callback_data="cat_Здоровье")
            ],
            [
                InlineKeyboardButton("🏠 Жилье", callback_data="cat_Жилье"),
                InlineKeyboardButton("🎮 Развлечения", callback_data="cat_Развлечения")
            ],
            [InlineKeyboardButton("✏️ Ввести свою", callback_data="cat_custom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Сумма: {format_currency(amount)} руб.\n\n"
            "Выбери категорию или введи свою:",
            reply_markup=reply_markup
        )
        return WAITING_FOR_CATEGORY
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи число (например: 1500):")
        return WAITING_FOR_AMOUNT


async def add_expense_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        if update.callback_query.data == "cat_custom":
            await update.callback_query.edit_message_text("Введи название категории:")
            return WAITING_FOR_CATEGORY
        else:
            category = update.callback_query.data.replace("cat_", "")
            context.user_data['expense_category'] = category
            await update.callback_query.edit_message_text(
                f"Категория: {category}\n\n"
                "Введи описание (или отправь /skip чтобы пропустить):"
            )
            return WAITING_FOR_DESCRIPTION
    else:
        category = update.message.text
        context.user_data['expense_category'] = category
        await update.message.reply_text(
            f"Категория: {category}\n\n"
            "Введи описание (или отправь /skip чтобы пропустить):"
        )
        return WAITING_FOR_DESCRIPTION


async def add_expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text and update.message.text.startswith('/skip'):
        description = None
    elif update.message:
        description = update.message.text
    else:
        description = None
    
    context.user_data['expense_description'] = description
    msg_obj = update.message if update.message else update.callback_query.message
    await msg_obj.reply_text(
        "Укажи дату расхода в формате ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ.\n"
        "Отправь /today для текущей даты или /skip чтобы использовать сейчас."
    )
    return WAITING_FOR_EXPENSE_DATE


async def add_expense_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = context.user_data['expense_amount']
    category = context.user_data['expense_category']
    description = context.user_data.get('expense_description')
    
    text = update.message.text if update.message else ''
    date_value = None
    if text.strip().lower() in ('/skip', ''):
        date_value = datetime.now()
    else:
        parsed_date = parse_user_date(text)
        if not parsed_date:
            await update.message.reply_text(
                "Не удалось разобрать дату. Используй формат ДД.ММ.ГГГГ (например, 05.08.2024) "
                "или ДД.ММ.ГГГГ ЧЧ:ММ."
            )
            return WAITING_FOR_EXPENSE_DATE
        date_value = parsed_date
    
    db.add_expense(user_id, amount, category, description, date_value)
    
    response_text = (
        f"✅ Расход добавлен!\n\n"
        f"💰 Сумма: {format_currency(amount)} руб.\n"
        f"📂 Категория: {category}\n"
        f"{f'📝 Описание: {description}\n' if description else ''}"
        f"📅 Дата: {format_date(date_value.isoformat())}"
    )
    
    # Проверка бюджета
    try:
        from budgets import budget_manager
        alert = budget_manager.check_budget_alerts(user_id, category)
        
        if alert:
            if alert['type'] == 'exceeded':
                response_text += (
                    f"\n\n🔴 <b>ПРЕВЫШЕН БЮДЖЕТ!</b>\n"
                    f"Лимит: {format_currency(alert['limit'])} руб.\n"
                    f"Потрачено: {format_currency(alert['spent'])} руб.\n"
                    f"Перерасход: {format_currency(alert['over'])} руб."
                )
            elif alert['type'] == 'warning':
                response_text += (
                    f"\n\n🟡 <b>Предупреждение!</b>\n"
                    f"Использовано {alert['percent']:.0f}% бюджета на '{category}'\n"
                    f"Осталось: {format_currency(alert['remaining'])} руб."
                )
    except Exception as e:
        print(f"Budget check error: {e}")
    
    await update.message.reply_text(response_text, parse_mode='HTML')
    
    context.user_data.clear()
    return ConversationHandler.END


def create_expense_delete_keyboard(expenses, page=0):
    """Создает клавиатуру с пагинацией для удаления расходов"""
    total_items = len(expenses)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
    
    buttons = []
    for exp in expenses[start_idx:end_idx]:
        date_value = format_date(exp['date']) if exp.get('date') else "Без даты"
        label = f"{format_currency(exp['amount'])} · {exp['category']} · {date_value}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"del_exp_{exp['id']}")])
    
    # Навигационные кнопки
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"exp_page_{page-1}"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"exp_page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Информация о странице
    if total_pages > 1:
        buttons.append([InlineKeyboardButton(
            f"Страница {page + 1} из {total_pages}",
            callback_data="exp_page_info"
        )])
    
    return InlineKeyboardMarkup(buttons)


async def show_delete_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    expenses = db.get_last_expenses(user_id, limit=50)  # Получаем больше записей для пагинации
    
    if not expenses:
        await update.message.reply_text("Пока нет расходов для удаления.")
        return
    
    # Сохраняем список расходов в контексте для пагинации
    context.user_data['delete_expenses_list'] = expenses
    context.user_data['delete_expenses_page'] = 0
    
    reply_markup = create_expense_delete_keyboard(expenses, 0)
    await update.message.reply_text(
        "Выбери расход для удаления:\n(Отсортировано по дате, новые сверху)",
        reply_markup=reply_markup
    )


async def handle_expense_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка навигации по страницам расходов"""
    await update.callback_query.answer()
    
    if update.callback_query.data == "exp_page_info":
        return
    
    page = int(update.callback_query.data.replace("exp_page_", ""))
    expenses = context.user_data.get('delete_expenses_list', [])
    
    if not expenses:
        await update.callback_query.edit_message_text("Список расходов устарел. Начни заново.")
        return
    
    context.user_data['delete_expenses_page'] = page
    reply_markup = create_expense_delete_keyboard(expenses, page)
    
    await update.callback_query.edit_message_text(
        "Выбери расход для удаления:\n(Отсортировано по дате, новые сверху)",
        reply_markup=reply_markup
    )


async def handle_delete_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    expense_id = int(update.callback_query.data.replace("del_exp_", ""))
    user_id = update.effective_user.id
    
    if db.delete_expense(user_id, expense_id):
        await update.callback_query.edit_message_text("✅ Расход удален.")
        # Очищаем данные пагинации
        context.user_data.pop('delete_expenses_list', None)
        context.user_data.pop('delete_expenses_page', None)
    else:
        await update.callback_query.edit_message_text("Не удалось найти расход. Возможно, он уже удален.")


expense_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ Добавить расход$"), add_expense_start)],
    states={
        WAITING_FOR_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_amount)],
        WAITING_FOR_CATEGORY: [
            CallbackQueryHandler(add_expense_category, pattern="^cat_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_category)
        ],
        WAITING_FOR_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_description),
            CommandHandler("skip", add_expense_description)
        ],
        WAITING_FOR_EXPENSE_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_date),
            CommandHandler("skip", add_expense_date),
            CommandHandler("today", add_expense_date)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)

delete_expense_handler = MessageHandler(filters.Regex("^❌ Удалить расход$"), show_delete_expenses)
delete_expense_callback = CallbackQueryHandler(handle_delete_expense, pattern="^del_exp_\\d+$")
expense_page_callback = CallbackQueryHandler(handle_expense_page_navigation, pattern="^exp_page_")

__all__ = [
    'expense_handler',
    'delete_expense_handler',
    'delete_expense_callback',
    'expense_page_callback',
    'add_expense_start',
    'show_delete_expenses',
    'handle_delete_expense',
    'handle_expense_page_navigation'
]