from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CommandHandler, filters
)
from database import Database
from utils import format_currency, format_date
from handlers.common import cancel
from config import WAITING_FOR_SEARCH_QUERY, BACK_BUTTON_TEXT

db = Database()

SEARCH_HINT = (
    "Введи ключевое слово для поиска по описанию, категории или источнику.\n"
    "Используй префикс «расход:» или «доход:», чтобы искать только в нужном типе.\n"
    "Пример: «расход:еда» или «доход:зарплата»."
)

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(SEARCH_HINT)
    return WAITING_FOR_SEARCH_QUERY

async def search_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    txn_type = "all"
    lowered = text.lower()
    if lowered.startswith("расход:"):
        txn_type = "expenses"
        text = text.split(":", 1)[1].strip()
    elif lowered.startswith("доход:"):
        txn_type = "income"
        text = text.split(":", 1)[1].strip()
    
    if not text:
        await update.message.reply_text("Запрос пустой. Попробуй снова или отправь /cancel.")
        return WAITING_FOR_SEARCH_QUERY
    
    results = db.search_transactions(user_id, text, txn_type, limit=10)
    response = []
    
    if txn_type in ("all", "expenses"):
        expenses = results["expenses"]
        if expenses:
            response.append("💸 Расходы:")
            for exp in expenses:
                desc = f" • {exp['description']}" if exp.get('description') else ""
                date_value = exp.get('date')
                response.append(
                    f"  • {format_currency(exp['amount'])} руб. — {exp['category']}{desc} "
                    f"({format_date(date_value) if date_value else 'Без даты'})"
                )
    
    if txn_type in ("all", "income"):
        incomes = results["income"]
        if incomes:
            response.append("💰 Доходы:")
            for inc in incomes:
                desc = f" • {inc['description']}" if inc.get('description') else ""
                date_value = inc.get('date')
                response.append(
                    f"  • {format_currency(inc['amount'])} руб. — {inc['source']}{desc} "
                    f"({format_date(date_value) if date_value else 'Без даты'})"
                )
    
    if not response:
        await update.message.reply_text("Ничего не найдено. Попробуй уточнить запрос.")
    else:
        await update.message.reply_text("\n".join(response))
    
    return ConversationHandler.END

search_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^🔍 Поиск$"), search_start)],
    states={
        WAITING_FOR_SEARCH_QUERY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, search_execute)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)

