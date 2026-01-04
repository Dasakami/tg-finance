"""
Обработчики Premium функций и подписок
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, filters
)
from subscription import subscription_manager
from category_filter import category_filter
from budgets import budget_manager
from database import Database
from utils import format_currency
from handlers.common import cancel
from config import BACK_BUTTON_TEXT

db = Database()

WAITING_FOR_FILTER_CATEGORY = 200
WAITING_FOR_FILTER_ACTION = 201
WAITING_FOR_EDIT_BUDGET_AMOUNT = 202


def premium_required(func):
    """Декоратор для проверки Premium подписки"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not subscription_manager.is_premium(user_id):
            keyboard = [[InlineKeyboardButton("⭐ Получить Premium", callback_data="show_premium")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = (
                "🔒 <b>Premium функция</b>\n\n"
                "Эта функция доступна только для Premium подписчиков.\n\n"
                "✨ Преимущества Premium:\n"
                "• Редактирование и удаление бюджетов\n"
                "• Фильтрация категорий в анализе\n"
                "• Детальная статистика\n"
                "• Приоритетная поддержка\n\n"
                "💎 Стоимость: всего 1 ⭐ на месяц!"
            )
            
            if update.callback_query:
                await update.callback_query.answer("Требуется Premium подписка", show_alert=True)
                await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
            return
        
        return await func(update, context)
    return wrapper


async def show_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о Premium"""
    user_id = update.effective_user.id
    sub = subscription_manager.get_subscription(user_id)
    
    if update.callback_query:
        await update.callback_query.answer()
    
    if sub['is_premium']:
        message = (
            f"⭐ <b>Premium подписка активна</b>\n\n"
            f"📅 Осталось дней: {sub['days_left']}\n"
            f"💫 Всего оплачено: {sub['stars_paid']} ⭐\n\n"
            "✨ Доступные функции:\n"
            "• Редактирование бюджетов\n"
            "• Фильтрация категорий\n"
            "• Расширенная аналитика\n\n"
            "Спасибо за поддержку! 💖"
        )
        
        keyboard = [[InlineKeyboardButton("💎 Продлить подписку", callback_data="buy_premium")]]
    else:
        message = (
            "✨ <b>Получи Premium</b>\n\n"
            "🎯 Что дает Premium:\n"
            "• Редактирование и удаление бюджетов\n"
            "• Фильтрация категорий в анализе и прогнозах\n"
            "• Детальная статистика по периодам\n"
            "• Приоритетная поддержка\n\n"
            "💰 Стоимость: всего 1 ⭐ на месяц\n\n"
            "🎁 Попробуй сейчас!"
        )
        
        keyboard = [[InlineKeyboardButton("⭐ Купить Premium (1 ⭐)", callback_data="buy_premium")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициировать покупку Premium"""
    await update.callback_query.answer()

    title = "Premium подписка на 1 месяц"
    description = "Доступ ко всем Premium функциям на 30 дней"
    payload = "premium_subscription_1_month"
    currency = "XTR"  
    prices = [LabeledPrice("Premium на месяц", 1)]  
    
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",  
        currency=currency,
        prices=prices
    )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение платежа"""
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешного платежа"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    
    success = subscription_manager.activate_premium(user_id, months=1)
    
    if success:
        subscription_manager.add_payment(
            user_id=user_id,
            stars_amount=1,
            payment_charge_id=payment.provider_payment_charge_id,
            telegram_payment_charge_id=payment.telegram_payment_charge_id
        )
        
        await update.message.reply_text(
            "🎉 <b>Поздравляем!</b>\n\n"
            "Premium подписка успешно активирована на 30 дней!\n\n"
            "✨ Теперь доступны все Premium функции:\n"
            "• Редактирование бюджетов\n"
            "• Фильтрация категорий\n"
            "• Расширенная аналитика\n\n"
            "Спасибо за поддержку! 💖",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ Произошла ошибка при активации подписки.\n"
            "Обратитесь в поддержку."
        )


@premium_required
async def edit_budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование бюджета"""
    await update.callback_query.answer()
    user_id = update.effective_user.id
    
    budgets = budget_manager.get_budgets(user_id)
    
    if not budgets:
        await update.callback_query.edit_message_text("У тебя нет бюджетов для редактирования.")
        return
    
    keyboard = []
    for budget in budgets:
        keyboard.append([
            InlineKeyboardButton(
                f"✏️ {budget['category']} ({format_currency(budget['limit_amount'])} руб.)",
                callback_data=f"edit_budget_{budget['category']}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "Выбери бюджет для редактирования:",
        reply_markup=reply_markup
    )


async def edit_budget_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Категория бюджета выбрана для редактирования"""
    await update.callback_query.answer()
    
    category = update.callback_query.data.replace("edit_budget_", "")
    context.user_data['edit_budget_category'] = category
    
    user_id = update.effective_user.id
    budgets = budget_manager.get_budgets(user_id)
    current_budget = next((b for b in budgets if b['category'] == category), None)
    
    if current_budget:
        await update.callback_query.edit_message_text(
            f"Текущий лимит для «{category}»: {format_currency(current_budget['limit_amount'])} руб.\n\n"
            "Введи новый лимит в рублях:"
        )
        return WAITING_FOR_EDIT_BUDGET_AMOUNT
    else:
        await update.callback_query.edit_message_text("Бюджет не найден.")
        return ConversationHandler.END


async def edit_budget_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить новый лимит бюджета"""
    try:
        amount = float(update.message.text.replace(',', '.'))
        if amount <= 0:
            await update.message.reply_text("Сумма должна быть положительной!")
            return WAITING_FOR_EDIT_BUDGET_AMOUNT
        
        user_id = update.effective_user.id
        category = context.user_data['edit_budget_category']
        
        success = budget_manager.set_budget(user_id, category, amount)
        
        if success:
            await update.message.reply_text(
                f"✅ Бюджет обновлен!\n\n"
                f"📂 Категория: {category}\n"
                f"💰 Новый лимит: {format_currency(amount)} руб./месяц"
            )
        else:
            await update.message.reply_text("❌ Ошибка при обновлении бюджета.")
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи число:")
        return WAITING_FOR_EDIT_BUDGET_AMOUNT


@premium_required
async def show_category_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню фильтров категорий"""
    user_id = update.effective_user.id
    filters = category_filter.get_all_filters(user_id)
    
    message = "🎯 <b>Фильтры категорий</b>\n\n"
    
    if filters['expense_excluded']:
        message += "❌ <b>Исключены из расходов:</b>\n"
        for cat in filters['expense_excluded']:
            message += f"  • {cat}\n"
        message += "\n"
    
    if filters['expense_included']:
        message += "✅ <b>Учитываются в расходах:</b>\n"
        for cat in filters['expense_included']:
            message += f"  • {cat}\n"
        message += "\n"
    
    if not filters['expense_excluded'] and not filters['expense_included']:
        message += "Фильтры не установлены. Все категории учитываются.\n\n"
    
    message += (
        "💡 <b>Как работают фильтры:</b>\n"
        "• Исключенные категории не учитываются в анализе\n"
        "• Если добавлены «только эти», учитываются только они\n"
        "• Фильтры влияют на советы, прогнозы и статистику"
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить фильтр", callback_data="add_filter")],
        [InlineKeyboardButton("🗑 Удалить фильтр", callback_data="remove_filter")],
        [InlineKeyboardButton("🔄 Очистить все", callback_data="clear_filters")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


async def add_filter_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать добавление фильтра"""
    await update.callback_query.answer()
    
    user_id = update.effective_user.id
    stats = db.get_statistics(user_id, 90)
    
    categories = list(stats['expenses_by_category'].keys())[:10]
    
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"filter_cat_{cat}")])
    
    keyboard.append([InlineKeyboardButton("✏️ Ввести вручную", callback_data="filter_cat_custom")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "Выбери категорию для фильтрации:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_FILTER_CATEGORY


async def filter_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Категория выбрана"""
    await update.callback_query.answer()
    
    if update.callback_query.data == "filter_cat_custom":
        await update.callback_query.edit_message_text(
            "Введи название категории:"
        )
        return WAITING_FOR_FILTER_CATEGORY
    
    category = update.callback_query.data.replace("filter_cat_", "")
    context.user_data['filter_category'] = category
    
    keyboard = [
        [InlineKeyboardButton("❌ Исключить из анализа", callback_data="filter_exclude")],
        [InlineKeyboardButton("✅ Учитывать только её", callback_data="filter_include")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        f"Категория: {category}\n\nВыбери действие:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_FILTER_ACTION


async def filter_category_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод категории вручную"""
    category = update.message.text.strip()
    context.user_data['filter_category'] = category
    
    keyboard = [
        [InlineKeyboardButton("❌ Исключить из анализа", callback_data="filter_exclude")],
        [InlineKeyboardButton("✅ Учитывать только её", callback_data="filter_include")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Категория: {category}\n\nВыбери действие:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_FILTER_ACTION


async def filter_action_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действие фильтра выбрано"""
    await update.callback_query.answer()
    
    user_id = update.effective_user.id
    category = context.user_data.get('filter_category')
    
    if not category:
        await update.callback_query.edit_message_text("Ошибка: категория не найдена")
        return ConversationHandler.END
    
    is_excluded = update.callback_query.data == "filter_exclude"
    
    success = category_filter.add_filter(user_id, category, is_excluded)
    
    if success:
        action_text = "исключена из" if is_excluded else "будет единственной учитываемой в"
        await update.callback_query.edit_message_text(
            f"✅ Категория «{category}» {action_text} анализе!"
        )
    else:
        await update.callback_query.edit_message_text("❌ Ошибка при добавлении фильтра")
    
    context.user_data.clear()
    return ConversationHandler.END


async def remove_filter_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать удаление фильтра"""
    await update.callback_query.answer()
    user_id = update.effective_user.id
    
    filters = category_filter.get_all_filters(user_id)
    all_filtered = filters['expense_excluded'] + filters['expense_included']
    
    if not all_filtered:
        await update.callback_query.edit_message_text("У тебя нет активных фильтров.")
        return
    
    keyboard = []
    for cat in all_filtered:
        keyboard.append([InlineKeyboardButton(f"🗑 {cat}", callback_data=f"rmfilter_{cat}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "Выбери фильтр для удаления:",
        reply_markup=reply_markup
    )


async def remove_filter_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтвердить удаление фильтра"""
    await update.callback_query.answer()
    
    category = update.callback_query.data.replace("rmfilter_", "")
    user_id = update.effective_user.id
    
    success = category_filter.remove_filter(user_id, category)
    
    if success:
        await update.callback_query.edit_message_text(f"✅ Фильтр «{category}» удален")
    else:
        await update.callback_query.edit_message_text("❌ Ошибка при удалении фильтра")


async def clear_all_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистить все фильтры"""
    await update.callback_query.answer()
    user_id = update.effective_user.id
    
    success = category_filter.clear_all_filters(user_id)
    
    if success:
        await update.callback_query.edit_message_text("✅ Все фильтры очищены")
    else:
        await update.callback_query.edit_message_text("У тебя нет активных фильтров")


filter_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_filter_start, pattern="^add_filter$")],
    states={
        WAITING_FOR_FILTER_CATEGORY: [
            CallbackQueryHandler(filter_category_selected, pattern="^filter_cat_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, filter_category_custom)
        ],
        WAITING_FOR_FILTER_ACTION: [
            CallbackQueryHandler(filter_action_selected, pattern="^filter_(exclude|include)$")
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)


edit_budget_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_budget_start, pattern="^budgets_edit$")],
    states={
        WAITING_FOR_EDIT_BUDGET_AMOUNT: [
            CallbackQueryHandler(edit_budget_category_selected, pattern="^edit_budget_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_budget_amount)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)


__all__ = [
    'show_premium_info',
    'buy_premium',
    'precheckout_callback',
    'successful_payment_callback',
    'show_category_filters',
    'filter_conversation',
    'edit_budget_conversation',
    'edit_budget_start',
    'remove_filter_start',
    'remove_filter_confirm',
    'clear_all_filters',
    'premium_required'
]