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

SEARCH_HINT = """🔍 Инструкция по поиску:

📝 Основные возможности:
• Поиск работает по описанию, категории расходов и источнику доходов
• Регистр букв не имеет значения
• Можно искать по части слова

🎯 Специальные префиксы:
• расход: или expense: — искать только в расходах
• доход: или income: — искать только в доходах

💡 Примеры использования:
• "еда" — найдет все записи со словом "еда"
• "расход:транспорт" — только расходы на транспорт
• "доход:зарплата" — только доходы от зарплаты
• "продукты" — все записи со словом "продукты"

Введи поисковый запрос:"""


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(SEARCH_HINT)
    return WAITING_FOR_SEARCH_QUERY


async def search_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    txn_type = "all"
    lowered = text.lower()
    
    # Проверка префиксов на русском и английском
    if lowered.startswith("расход:") or lowered.startswith("expense:"):
        txn_type = "expenses"
        text = text.split(":", 1)[1].strip()
    elif lowered.startswith("доход:") or lowered.startswith("income:"):
        txn_type = "income"
        text = text.split(":", 1)[1].strip()
    
    if not text:
        await update.message.reply_text(
            "❌ Запрос пустой. Введи поисковое слово или фразу.\n"
            "Отправь /cancel для выхода из режима поиска."
        )
        return WAITING_FOR_SEARCH_QUERY
    
    results = db.search_transactions(user_id, text, txn_type, limit=15)
    response = []
    total_found = len(results["expenses"]) + len(results["income"])
    
    if total_found == 0:
        await update.message.reply_text(
            f"🔍 По запросу «{text}» ничего не найдено.\n\n"
            "💡 Советы:\n"
            "• Проверь правильность написания\n"
            "• Попробуй использовать часть слова\n"
            "• Используй префиксы расход:/доход: для точного поиска"
        )
        return ConversationHandler.END
    
    response.append(f"🔍 Найдено записей: {total_found}\n")
    
    if txn_type in ("all", "expenses"):
        expenses = results["expenses"]
        if expenses:
            response.append(f"💸 Расходы ({len(expenses)}):")
            for exp in expenses:
                desc = f" • {exp['description']}" if exp.get('description') else ""
                date_value = exp.get('date')
                date_str = format_date(date_value) if date_value else "Без даты"
                response.append(
                    f"  • {format_currency(exp['amount'])} руб. — {exp['category']}{desc}\n"
                    f"    📅 {date_str}"
                )
            response.append("")
    
    if txn_type in ("all", "income"):
        incomes = results["income"]
        if incomes:
            response.append(f"💰 Доходы ({len(incomes)}):")
            for inc in incomes:
                desc = f" • {inc['description']}" if inc.get('description') else ""
                date_value = inc.get('date')
                date_str = format_date(date_value) if date_value else "Без даты"
                response.append(
                    f"  • {format_currency(inc['amount'])} руб. — {inc['source']}{desc}\n"
                    f"    📅 {date_str}"
                )
    
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