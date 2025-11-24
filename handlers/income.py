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
    WAITING_FOR_INCOME_AMOUNT,
    WAITING_FOR_INCOME_SOURCE,
    WAITING_FOR_INCOME_DESCRIPTION,
    WAITING_FOR_INCOME_DATE,
    BACK_BUTTON_TEXT
)

db = Database()

ITEMS_PER_PAGE = 5


async def add_income_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи сумму дохода (например: 50000 или 1500.75):")
    return WAITING_FOR_INCOME_AMOUNT


async def add_income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(',', '.'))
        if amount <= 0:
            await update.message.reply_text("Сумма должна быть положительным числом. Попробуй еще раз:")
            return WAITING_FOR_INCOME_AMOUNT
        
        context.user_data['income_amount'] = amount
        
        keyboard = [
            [
                InlineKeyboardButton("💼 Зарплата", callback_data="src_Зарплата"),
                InlineKeyboardButton("💻 Фриланс", callback_data="src_Фриланс")
            ],
            [
                InlineKeyboardButton("📈 Инвестиции", callback_data="src_Инвестиции"),
                InlineKeyboardButton("🏪 Бизнес", callback_data="src_Бизнес")
            ],
            [
                InlineKeyboardButton("🎁 Подарки", callback_data="src_Подарки"),
                InlineKeyboardButton("💰 Прочее", callback_data="src_Прочее")
            ],
            [InlineKeyboardButton("✏️ Ввести свой", callback_data="src_custom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Сумма: {format_currency(amount)} руб.\n\n"
            "Выбери источник дохода или введи свой:",
            reply_markup=reply_markup
        )
        return WAITING_FOR_INCOME_SOURCE
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи число (например: 50000):")
        return WAITING_FOR_INCOME_AMOUNT


async def add_income_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        if update.callback_query.data == "src_custom":
            await update.callback_query.edit_message_text("Введи источник дохода:")
            return WAITING_FOR_INCOME_SOURCE
        else:
            source = update.callback_query.data.replace("src_", "")
            context.user_data['income_source'] = source
            await update.callback_query.edit_message_text(
                f"Источник: {source}\n\n"
                "Введи описание (или отправь /skip чтобы пропустить):"
            )
            return WAITING_FOR_INCOME_DESCRIPTION
    else:
        source = update.message.text
        context.user_data['income_source'] = source
        await update.message.reply_text(
            f"Источник: {source}\n\n"
            "Введи описание (или отправь /skip чтобы пропустить):"
        )
        return WAITING_FOR_INCOME_DESCRIPTION


async def add_income_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text and update.message.text.startswith('/skip'):
        description = None
    elif update.message:
        description = update.message.text
    else:
        description = None
    
    context.user_data['income_description'] = description
    msg_obj = update.message if update.message else update.callback_query.message
    await msg_obj.reply_text(
        "Укажи дату дохода в формате ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ.\n"
        "Отправь /today для текущей даты или /skip чтобы использовать сейчас."
    )
    return WAITING_FOR_INCOME_DATE


async def add_income_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = context.user_data['income_amount']
    source = context.user_data['income_source']
    description = context.user_data.get('income_description')
    
    text = update.message.text if update.message else ''
    if text.strip().lower() in ('/skip', ''):
        date_value = datetime.now()
    else:
        parsed_date = parse_user_date(text)
        if not parsed_date:
            await update.message.reply_text(
                "Не удалось разобрать дату. Используй формат ДД.ММ.ГГГГ (например, 05.08.2024) "
                "или ДД.ММ.ГГГГ ЧЧ:ММ."
            )
            return WAITING_FOR_INCOME_DATE
        date_value = parsed_date
    
    db.add_income(user_id, amount, source, description, date_value)
    
    await update.message.reply_text(
        f"✅ Доход добавлен!\n\n"
        f"💰 Сумма: {format_currency(amount)} руб.\n"
        f"📂 Источник: {source}\n"
        f"{f'📝 Описание: {description}\n' if description else ''}"
        f"📅 Дата: {format_date(date_value.isoformat())}"
    )
    
    context.user_data.clear()
    return ConversationHandler.END


def create_income_delete_keyboard(incomes, page=0):
    """Создает клавиатуру с пагинацией для удаления доходов"""
    total_items = len(incomes)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
    
    buttons = []
    for inc in incomes[start_idx:end_idx]:
        date_value = format_date(inc['date']) if inc.get('date') else "Без даты"
        label = f"{format_currency(inc['amount'])} · {inc['source']} · {date_value}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"del_inc_{inc['id']}")])
    
    # Навигационные кнопки
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"inc_page_{page-1}"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"inc_page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Информация о странице
    if total_pages > 1:
        buttons.append([InlineKeyboardButton(
            f"Страница {page + 1} из {total_pages}",
            callback_data="inc_page_info"
        )])
    
    return InlineKeyboardMarkup(buttons)


async def show_delete_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    incomes = db.get_last_income(user_id, limit=50)  # Получаем больше записей для пагинации
    
    if not incomes:
        await update.message.reply_text("Пока нет доходов для удаления.")
        return
    
    # Сохраняем список доходов в контексте для пагинации
    context.user_data['delete_income_list'] = incomes
    context.user_data['delete_income_page'] = 0
    
    reply_markup = create_income_delete_keyboard(incomes, 0)
    await update.message.reply_text(
        "Выбери доход для удаления:\n(Отсортировано по дате, новые сверху)",
        reply_markup=reply_markup
    )


async def handle_income_page_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка навигации по страницам доходов"""
    await update.callback_query.answer()
    
    if update.callback_query.data == "inc_page_info":
        return
    
    page = int(update.callback_query.data.replace("inc_page_", ""))
    incomes = context.user_data.get('delete_income_list', [])
    
    if not incomes:
        await update.callback_query.edit_message_text("Список доходов устарел. Начни заново.")
        return
    
    context.user_data['delete_income_page'] = page
    reply_markup = create_income_delete_keyboard(incomes, page)
    
    await update.callback_query.edit_message_text(
        "Выбери доход для удаления:\n(Отсортировано по дате, новые сверху)",
        reply_markup=reply_markup
    )


async def handle_delete_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    income_id = int(update.callback_query.data.replace("del_inc_", ""))
    user_id = update.effective_user.id
    
    if db.delete_income(user_id, income_id):
        await update.callback_query.edit_message_text("✅ Доход удален.")
        # Очищаем данные пагинации
        context.user_data.pop('delete_income_list', None)
        context.user_data.pop('delete_income_page', None)
    else:
        await update.callback_query.edit_message_text("Не удалось найти доход. Возможно, он уже удален.")


income_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^💰 Добавить доход$"), add_income_start)],
    states={
        WAITING_FOR_INCOME_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income_amount)],
        WAITING_FOR_INCOME_SOURCE: [
            CallbackQueryHandler(add_income_source, pattern="^src_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_income_source)
        ],
        WAITING_FOR_INCOME_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_income_description),
            CommandHandler("skip", add_income_description)
        ],
        WAITING_FOR_INCOME_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_income_date),
            CommandHandler("skip", add_income_date),
            CommandHandler("today", add_income_date)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)

delete_income_handler = MessageHandler(filters.Regex("^✅ Удалить доход$"), show_delete_income)
delete_income_callback = CallbackQueryHandler(handle_delete_income, pattern="^del_inc_\\d+$")
income_page_callback = CallbackQueryHandler(handle_income_page_navigation, pattern="^inc_page_")

__all__ = [
    'income_handler',
    'delete_income_handler', 
    'delete_income_callback',
    'income_page_callback',
    'add_income_start',
    'show_delete_income',
    'handle_delete_income',
    'handle_income_page_navigation'
]