from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CommandHandler, CallbackQueryHandler, filters
)
from balance import balance_manager
from utils import format_currency, format_date
from handlers.common import cancel
from config import BACK_BUTTON_TEXT

WAITING_FOR_HIDDEN_AMOUNT = 400
WAITING_FOR_HIDDEN_REASON = 401


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = balance_manager.get_balance(user_id)
    
    message = "💰 <b>Твой баланс</b>\n\n"
    message += f"💵 Основной: {format_currency(balance['balance'])} руб.\n"
    message += f"🔒 Скрытый: {format_currency(balance['hidden_balance'])} руб.\n"
    message += f"━━━━━━━━━━━━━━━━\n"
    message += f"📊 <b>Всего: {format_currency(balance['total_balance'])} руб.</b>\n\n"
    message += "💡 Скрытый баланс — это твои отложенные деньги"
    
    keyboard = [
        [
            InlineKeyboardButton("➕ В скрытое", callback_data="hidden_add"),
            InlineKeyboardButton("➖ Из скрытого", callback_data="hidden_remove")
        ],
        [InlineKeyboardButton("📜 История", callback_data="hidden_history")],
        [InlineKeyboardButton("🔄 Пересчитать", callback_data="balance_recalc")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


async def hidden_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    
    user_id = update.effective_user.id
    balance = balance_manager.get_balance(user_id)
    
    await update.callback_query.edit_message_text(
        f"💰 Доступно на основном балансе: {format_currency(balance['balance'])} руб.\n\n"
        "Сколько хочешь отложить в скрытое?",
        parse_mode='HTML'
    )
    
    context.user_data['hidden_operation'] = 'add'
    return WAITING_FOR_HIDDEN_AMOUNT


async def hidden_remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать возврат из скрытого"""
    await update.callback_query.answer()
    
    user_id = update.effective_user.id
    balance = balance_manager.get_balance(user_id)
    
    if balance['hidden_balance'] <= 0:
        await update.callback_query.edit_message_text(
            "❌ В скрытом балансе нет денег."
        )
        return ConversationHandler.END
    
    await update.callback_query.edit_message_text(
        f"🔒 В скрытом: {format_currency(balance['hidden_balance'])} руб.\n\n"
        "Сколько хочешь вернуть на основной баланс?",
        parse_mode='HTML'
    )
    
    context.user_data['hidden_operation'] = 'remove'
    return WAITING_FOR_HIDDEN_AMOUNT


async def hidden_amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введённой суммы"""
    try:
        amount = float(update.message.text.replace(',', '.'))
        if amount <= 0:
            await update.message.reply_text("Сумма должна быть положительной!")
            return WAITING_FOR_HIDDEN_AMOUNT
        
        context.user_data['hidden_amount'] = amount
        
        await update.message.reply_text(
            "Укажи причину (необязательно) или отправь /skip:"
        )
        return WAITING_FOR_HIDDEN_REASON
        
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи число:")
        return WAITING_FOR_HIDDEN_AMOUNT


async def hidden_reason_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка причины и выполнение операции"""
    user_id = update.effective_user.id
    operation = context.user_data.get('hidden_operation')
    amount = context.user_data.get('hidden_amount')
    
    if update.message.text.startswith('/skip'):
        reason = None
    else:
        reason = update.message.text
    
    if operation == 'add':
        success = balance_manager.add_to_hidden(user_id, amount, reason)
        if success:
            new_balance = balance_manager.get_balance(user_id)
            await update.message.reply_text(
                f"✅ Отложено в скрытое: {format_currency(amount)} руб.\n\n"
                f"💵 Основной баланс: {format_currency(new_balance['balance'])} руб.\n"
                f"🔒 Скрытый баланс: {format_currency(new_balance['hidden_balance'])} руб.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ Недостаточно средств на основном балансе."
            )
    else:  
        success = balance_manager.remove_from_hidden(user_id, amount, reason)
        if success:
            new_balance = balance_manager.get_balance(user_id)
            await update.message.reply_text(
                f"✅ Возвращено из скрытого: {format_currency(amount)} руб.\n\n"
                f"💵 Основной баланс: {format_currency(new_balance['balance'])} руб.\n"
                f"🔒 Скрытый баланс: {format_currency(new_balance['hidden_balance'])} руб.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ Недостаточно средств в скрытом балансе."
            )
    
    context.user_data.clear()
    return ConversationHandler.END


async def show_hidden_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать историю операций со скрытым балансом"""
    await update.callback_query.answer()
    
    user_id = update.effective_user.id
    history = balance_manager.get_hidden_history(user_id, limit=15)
    
    if not history:
        await update.callback_query.edit_message_text(
            "📜 История операций пуста."
        )
        return
    
    message = "📜 <b>История скрытого баланса</b>\n\n"
    
    for h in history:
        date_str = format_date(h['date'].isoformat() if hasattr(h['date'], 'isoformat') else str(h['date']))
        operation = "➕ Добавлено" if h['operation_type'] == 'add' else "➖ Снято"
        amount_str = format_currency(h['amount'])
        reason = f"\n   💬 {h['reason']}" if h['reason'] else ""
        
        message += f"{operation}: {amount_str} руб.\n"
        message += f"   📅 {date_str}{reason}\n\n"
    
    await update.callback_query.edit_message_text(message, parse_mode='HTML')


async def recalculate_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересчитать баланс"""
    await update.callback_query.answer("Пересчитываю...")
    
    user_id = update.effective_user.id
    balance_manager.recalculate_balance(user_id)
    
    new_balance = balance_manager.get_balance(user_id)
    
    await update.callback_query.edit_message_text(
        f"✅ <b>Баланс пересчитан</b>\n\n"
        f"💵 Основной: {format_currency(new_balance['balance'])} руб.\n"
        f"🔒 Скрытый: {format_currency(new_balance['hidden_balance'])} руб.\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Всего: {format_currency(new_balance['total_balance'])} руб.</b>",
        parse_mode='HTML'
    )


hidden_balance_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(hidden_add_start, pattern="^hidden_add$"),
        CallbackQueryHandler(hidden_remove_start, pattern="^hidden_remove$")
    ],
    states={
        WAITING_FOR_HIDDEN_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_amount_entered)
        ],
        WAITING_FOR_HIDDEN_REASON: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, hidden_reason_entered),
            CommandHandler("skip", hidden_reason_entered)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)


__all__ = [
    'show_balance',
    'show_hidden_history',
    'recalculate_balance',
    'hidden_balance_conversation'
]