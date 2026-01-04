"""
Обработчики для Inline режима
Позволяет добавлять операции из любого чата
"""
import re
from uuid import uuid4
from telegram import (
    Update, InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import ContextTypes
from database import Database

db = Database()


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик inline запросов
    
    Примеры:
    - @bot расход 500 еда
    - @bot доход 5000 зарплата
    - @bot expense 1500 transport
    - @bot income 3000 freelance
    """
    query = update.inline_query.query.strip()
    user_id = update.inline_query.from_user.id
    
    if not query:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="💸 Добавить расход",
                description="Формат: расход СУММА КАТЕГОРИЯ [описание]",
                input_message_content=InputTextMessageContent(
                    "Пример: расход 500 еда обед в кафе"
                ),
                thumb_url="https://img.icons8.com/color/96/000000/money-bag.png"
            ),
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="💰 Добавить доход",
                description="Формат: доход СУММА ИСТОЧНИК [описание]",
                input_message_content=InputTextMessageContent(
                    "Пример: доход 5000 зарплата премия"
                ),
                thumb_url="https://img.icons8.com/color/96/000000/receive-cash.png"
            ),
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="📊 Показать статистику",
                description="Быстрый просмотр статистики за месяц",
                input_message_content=InputTextMessageContent("📊 Статистика за месяц"),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📈 Открыть бота", url=f"t.me/{context.bot.username}")
                ]])
            )
        ]
        await update.inline_query.answer(results, cache_time=10)
        return
    
    parsed = parse_inline_command(query)
    
    if not parsed:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="❌ Неверный формат",
                description="Используй: расход/доход СУММА КАТЕГОРИЯ [описание]",
                input_message_content=InputTextMessageContent(
                    "Примеры команд:\n"
                    "• расход 500 еда\n"
                    "• доход 5000 зарплата\n"
                    "• расход 1500 транспорт такси домой"
                )
            )
        ]
        await update.inline_query.answer(results, cache_time=1)
        return
    
    results = []
    
    if parsed['type'] == 'expense':
        context.user_data[f'inline_expense_{user_id}'] = parsed
        
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"💸 Добавить расход {parsed['amount']} руб.",
                description=f"Категория: {parsed['category']}" + (f" | {parsed['description']}" if parsed['description'] else ""),
                input_message_content=InputTextMessageContent(
                    f"✅ Расход добавлен!\n\n"
                    f"💰 Сумма: {parsed['amount']:,.0f} руб.\n"
                    f"📂 Категория: {parsed['category']}\n" +
                    (f"📝 Описание: {parsed['description']}" if parsed['description'] else "")
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Статистика", callback_data="inline_stats"),
                    InlineKeyboardButton("🤖 Открыть бота", url=f"t.me/{context.bot.username}")
                ]])
            )
        )
        
        db.add_expense(
            user_id=user_id,
            amount=parsed['amount'],
            category=parsed['category'],
            description=parsed['description']
        )
        
    elif parsed['type'] == 'income':
        context.user_data[f'inline_income_{user_id}'] = parsed
        
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"💰 Добавить доход {parsed['amount']} руб.",
                description=f"Источник: {parsed['source']}" + (f" | {parsed['description']}" if parsed['description'] else ""),
                input_message_content=InputTextMessageContent(
                    f"✅ Доход добавлен!\n\n"
                    f"💰 Сумма: {parsed['amount']:,.0f} руб.\n"
                    f"📂 Источник: {parsed['source']}\n" +
                    (f"📝 Описание: {parsed['description']}" if parsed['description'] else "")
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Статистика", callback_data="inline_stats"),
                    InlineKeyboardButton("🤖 Открыть бота", url=f"t.me/{context.bot.username}")
                ]])
            )
        )
        db.add_income(
            user_id=user_id,
            amount=parsed['amount'],
            source=parsed['source'],
            description=parsed['description']
        )
    
    await update.inline_query.answer(results, cache_time=1)


def parse_inline_command(query: str) -> dict:
    """
    Парсит inline команду
    
    Форматы:
    - расход 500 еда
    - расход 500 еда обед в кафе
    - доход 5000 зарплата
    - expense 1500 transport taxi home
    """
    query = query.lower().strip()
    
    operation_type = None
    if query.startswith(('расход', 'expense', 'трата')):
        operation_type = 'expense'
    elif query.startswith(('доход', 'income', 'приход')):
        operation_type = 'income'
    else:
        return None
    
    for keyword in ['расход', 'expense', 'трата', 'доход', 'income', 'приход']:
        if query.startswith(keyword):
            query = query[len(keyword):].strip()
            break
    
    parts = query.split(maxsplit=2)
    
    if len(parts) < 2:
        return None
    
    try:
        amount = float(parts[0].replace(',', '.'))
        if amount <= 0:
            return None
    except (ValueError, IndexError):
        return None
    
    category_or_source = parts[1]

    description = parts[2] if len(parts) > 2 else None
    
    result = {
        'type': operation_type,
        'amount': amount,
        'description': description
    }
    
    if operation_type == 'expense':
        result['category'] = category_or_source
    else:
        result['source'] = category_or_source
    
    return result


async def inline_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрая статистика через inline кнопку"""
    await update.callback_query.answer()
    user_id = update.callback_query.from_user.id
    
    stats = db.get_statistics(user_id, 30)
    
    message = (
        "📊 <b>Статистика за 30 дней</b>\n\n"
        f"💰 Доходы: {stats['total_income']:,.0f} руб.\n"
        f"💸 Расходы: {stats['total_expenses']:,.0f} руб.\n"
        f"💵 Баланс: {stats['balance']:,.0f} руб.\n\n"
        f"📝 Операций: {stats['expenses_count'] + stats['income_count']}"
    )
    
    await update.callback_query.message.reply_text(
        message,
        parse_mode='HTML'
    )


async def chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбранного inline результата"""
    result = update.chosen_inline_result
    user_id = result.from_user.id
    
    print(f"User {user_id} used inline mode: {result.query}")


__all__ = [
    'inline_query_handler',
    'inline_stats_callback',
    'chosen_inline_result'
]