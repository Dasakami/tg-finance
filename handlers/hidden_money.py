from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler
)

from config import (
    WAITING_FOR_BULK_TYPE,
    WAITING_FOR_BULK_DATA,
    BACK_BUTTON_TEXT
)
from database import Database
from handlers.common import cancel
from utils import parse_user_date, format_currency, format_date
from hidden import HiddenMoneyManager

db = Database()

hidden_money_manager = HiddenMoneyManager()

async def add_hidden_money_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать добавление скрытых денег"""
    await update.message.reply_text(
        "Введите сумму скрытых денег, которые вы хотите добавить:",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(BACK_BUTTON_TEXT, callback_data='cancel')
        )
    )
    return WAITING_FOR_BULK_TYPE

async def add_hidden_money_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать сумму скрытых денег"""
    try:
        amount = float(update.message.text)
        context.user_data['hidden_money_amount'] = amount
        await update.message.reply_text(
            "Введите причину (необязательно):",
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(BACK_BUTTON_TEXT, callback_data='cancel')
            )
        )
        return WAITING_FOR_BULK_DATA
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректную числовую сумму.")
        return WAITING_FOR_BULK_TYPE
    
async def add_hidden_money_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработать причину скрытых денег и сохранить запись"""
    reason = update.message.text
    amount = context.user_data.get('hidden_money_amount')
    user_id = update.effective_user.id
    minus_money_from_balance = db.add_expense(
        user_id=user_id,
        amount=amount,
        category="Скрытые деньги",
        description=f"Добавление скрытых денег. Причина: {reason}" if reason else "Добавление скрытых денег",
        date=datetime.now()
    )
    success = hidden_money_manager.add_hidden_money(user_id, amount, reason)

    
    if success:
        await update.message.reply_text(
            f"✅ Скрытые деньги в размере {format_currency(amount)} успешно добавлены!"
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при добавлении скрытых денег. Пожалуйста, попробуйте снова."
        )
    
    return ConversationHandler.END


