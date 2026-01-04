"""
Обработчики для уведомлений и регулярных трат
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CommandHandler, CallbackQueryHandler, filters
)
from notifications import notification_manager
from utils import format_currency, format_date
from handlers.common import cancel
from config import BACK_BUTTON_TEXT

WAITING_FOR_REGULAR_CATEGORY = 600
WAITING_FOR_REGULAR_AMOUNT = 601
WAITING_FOR_REGULAR_FREQUENCY = 602


async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать настройки уведомлений"""
    user_id = update.effective_user.id
    settings = notification_manager.get_settings(user_id)
    
    message = "🔔 <b>Настройки уведомлений</b>\n\n"
    
    status_emoji = lambda x: "✅" if x else "❌"
    
    message += f"{status_emoji(settings['daily_summary'])} Ежедневная сводка\n"
    message += f"{status_emoji(settings['weekly_report'])} Недельный отчёт\n"
    message += f"{status_emoji(settings['budget_alerts'])} Предупреждения о бюджете\n"
    message += f"{status_emoji(settings['large_expense_alert'])} Крупные траты"
    message += f" (от {format_currency(settings['large_expense_threshold'])} руб.)\n"
    message += f"{status_emoji(settings['regular_expense_reminders'])} Напоминания о регулярных тратах\n\n"
    message += "Нажми на кнопку, чтобы изменить настройку:"
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'✅' if settings['daily_summary'] else '❌'} Ежедневная сводка",
            callback_data="notif_toggle_daily_summary"
        )],
        [InlineKeyboardButton(
            f"{'✅' if settings['weekly_report'] else '❌'} Недельный отчёт",
            callback_data="notif_toggle_weekly_report"
        )],
        [InlineKeyboardButton(
            f"{'✅' if settings['budget_alerts'] else '❌'} Предупреждения о бюджете",
            callback_data="notif_toggle_budget_alerts"
        )],
        [InlineKeyboardButton(
            f"{'✅' if settings['large_expense_alert'] else '❌'} Крупные траты",
            callback_data="notif_toggle_large_expense_alert"
        )],
        [InlineKeyboardButton(
            f"{'✅' if settings['regular_expense_reminders'] else '❌'} Регулярные траты",
            callback_data="notif_toggle_regular_expense_reminders"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


async def toggle_notification_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить настройку уведомления"""
    await update.callback_query.answer()
    
    setting_name = update.callback_query.data.replace("notif_toggle_", "")
    user_id = update.effective_user.id
    
    settings = notification_manager.get_settings(user_id)
    current_value = settings[setting_name]
    new_value = 0 if current_value else 1
    
    notification_manager.update_settings(user_id, **{setting_name: new_value})
    
    setting_names = {
        'daily_summary': 'Ежедневная сводка',
        'weekly_report': 'Недельный отчёт',
        'budget_alerts': 'Предупреждения о бюджете',
        'large_expense_alert': 'Крупные траты',
        'regular_expense_reminders': 'Регулярные траты'
    }
    
    status = "включена" if new_value else "выключена"
    
    await update.callback_query.edit_message_text(
        f"✅ Настройка '{setting_names[setting_name]}' {status}!"
    )


async def show_regular_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список регулярных трат"""
    user_id = update.effective_user.id
    expenses = notification_manager.get_regular_expenses(user_id)
    
    if not expenses:
        keyboard = [[InlineKeyboardButton("➕ Добавить регулярную трату", callback_data="add_regular_expense")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⏰ У тебя пока нет регулярных трат.\n\n"
            "Добавь их, чтобы получать напоминания!",
            reply_markup=reply_markup
        )
        return
    
    message = "⏰ <b>Регулярные траты</b>\n\n"
    
    freq_names = {
        'daily': 'Ежедневно',
        'weekly': 'Еженедельно',
        'monthly': 'Ежемесячно'
    }
    
    keyboard = []
    
    for exp in expenses:
        next_date = format_date(exp['next_reminder'].isoformat() if hasattr(exp['next_reminder'], 'isoformat') else str(exp['next_reminder']))
        
        message += f"📂 <b>{exp['category']}</b>\n"
        message += f"💰 {format_currency(exp['amount'])} руб. - {freq_names.get(exp['frequency'], exp['frequency'])}\n"
        if exp['description']:
            message += f"📝 {exp['description']}\n"
        message += f"⏰ Следующее напоминание: {next_date}\n\n"
        
        keyboard.append([InlineKeyboardButton(
            f"🗑 Удалить: {exp['category']}",
            callback_data=f"disable_regular_{exp['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить ещё", callback_data="add_regular_expense")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


async def add_regular_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать добавление регулярной траты"""
    await update.callback_query.answer()
    
    await update.callback_query.edit_message_text(
        "⏰ <b>Добавление регулярной траты</b>\n\n"
        "Введи категорию (например: Интернет, Спортзал):",
        parse_mode='HTML'
    )
    
    return WAITING_FOR_REGULAR_CATEGORY


async def regular_category_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка категории регулярной траты"""
    category = update.message.text.strip()
    context.user_data['regular_category'] = category
    
    await update.message.reply_text(
        f"Категория: {category}\n\n"
        "Введи сумму в рублях:"
    )
    
    return WAITING_FOR_REGULAR_AMOUNT


async def regular_amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка суммы регулярной траты"""
    try:
        amount = float(update.message.text.replace(',', '.'))
        if amount <= 0:
            await update.message.reply_text("Сумма должна быть положительной!")
            return WAITING_FOR_REGULAR_AMOUNT
        
        context.user_data['regular_amount'] = amount
        
        keyboard = [
            [InlineKeyboardButton("📅 Ежедневно", callback_data="freq_daily")],
            [InlineKeyboardButton("📆 Еженедельно", callback_data="freq_weekly")],
            [InlineKeyboardButton("📊 Ежемесячно", callback_data="freq_monthly")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Сумма: {format_currency(amount)} руб.\n\n"
            "Как часто повторяется эта трата?",
            reply_markup=reply_markup
        )
        
        return WAITING_FOR_REGULAR_FREQUENCY
        
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи число:")
        return WAITING_FOR_REGULAR_AMOUNT


async def regular_frequency_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка частоты регулярной траты"""
    await update.callback_query.answer()
    
    frequency = update.callback_query.data.replace("freq_", "")
    user_id = update.effective_user.id
    
    category = context.user_data['regular_category']
    amount = context.user_data['regular_amount']
    
    success = notification_manager.add_regular_expense(
        user_id, category, amount, frequency
    )
    
    if success:
        freq_names = {
            'daily': 'ежедневно',
            'weekly': 'еженедельно',
            'monthly': 'ежемесячно'
        }
        
        await update.callback_query.edit_message_text(
            f"✅ Регулярная трата добавлена!\n\n"
            f"📂 {category}\n"
            f"💰 {format_currency(amount)} руб.\n"
            f"⏰ Напоминание: {freq_names[frequency]}\n\n"
            "Ты будешь получать напоминания об этой трате."
        )
    else:
        await update.callback_query.edit_message_text(
            "❌ Ошибка при добавлении регулярной траты."
        )
    
    context.user_data.clear()
    return ConversationHandler.END


async def disable_regular_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отключить регулярную трату"""
    await update.callback_query.answer()
    
    expense_id = int(update.callback_query.data.replace("disable_regular_", ""))
    
    success = notification_manager.disable_regular_expense(expense_id)
    
    if success:
        await update.callback_query.edit_message_text(
            "✅ Регулярная трата отключена."
        )
    else:
        await update.callback_query.edit_message_text(
            "❌ Не удалось отключить регулярную трату."
        )


regular_expense_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_regular_expense_start, pattern="^add_regular_expense$")],
    states={
        WAITING_FOR_REGULAR_CATEGORY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, regular_category_entered)
        ],
        WAITING_FOR_REGULAR_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, regular_amount_entered)
        ],
        WAITING_FOR_REGULAR_FREQUENCY: [
            CallbackQueryHandler(regular_frequency_selected, pattern="^freq_")
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)


__all__ = [
    'show_notification_settings',
    'toggle_notification_setting',
    'show_regular_expenses',
    'disable_regular_expense',
    'regular_expense_conversation'
]