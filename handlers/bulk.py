from typing import List, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CommandHandler, CallbackQueryHandler, filters
)

from config import (
    WAITING_FOR_BULK_TYPE,
    WAITING_FOR_BULK_DATA,
    WAITING_FOR_BULK_DELETE_TYPE,
    WAITING_FOR_BULK_DELETE_IDS,
    BACK_BUTTON_TEXT
)
from database import Database
from handlers.common import cancel
from utils import parse_user_date, format_currency, format_date

db = Database()

BULK_ADD_HINT = (
    "Введи операции построчно в формате:\n"
    "сумма; категория/источник; описание (опционально); дата (опционально)\n\n"
    "Пример:\n"
    "1500; Еда; Обед; 12.11.2025 13:00\n"
    "800; Транспорт\n"
    "Если дата не указана — возьмем текущую."
)

def _parse_bulk_lines(text: str, record_type: str) -> Tuple[List[dict], List[str]]:
    entries = []
    errors = []
    
    for idx, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(';')]
        if len(parts) < 2:
            errors.append(f"Строка {idx}: нужно минимум «сумма; категория/источник».")
            continue
        amount_text = parts[0].replace(',', '.')
        try:
            amount = float(amount_text)
        except ValueError:
            errors.append(f"Строка {idx}: не удалось разобрать сумму «{parts[0]}».")
            continue
        if amount <= 0:
            errors.append(f"Строка {idx}: сумма должна быть положительной.")
            continue
        
        entry = {'amount': amount}
        if record_type == 'expenses':
            entry['category'] = parts[1]
        else:
            entry['source'] = parts[1]
        
        description = parts[2] if len(parts) >= 3 and parts[2] else None
        if description:
            entry['description'] = description
        
        if len(parts) >= 4 and parts[3]:
            parsed_date = parse_user_date(parts[3])
            if not parsed_date:
                errors.append(f"Строка {idx}: не удалось разобрать дату «{parts[3]}».")
                continue
            entry['date'] = parsed_date
        
        entries.append(entry)
    
    return entries, errors

async def bulk_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Расходы", callback_data="bulk_add_expenses"),
            InlineKeyboardButton("Доходы", callback_data="bulk_add_income")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Что будем добавлять массово?", reply_markup=reply_markup)
    return WAITING_FOR_BULK_TYPE

async def bulk_add_choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    record_type = update.callback_query.data.replace("bulk_add_", "")
    context.user_data['bulk_add_type'] = record_type
    await update.callback_query.edit_message_text(
        f"Выбран тип: {'расходы' if record_type == 'expenses' else 'доходы'}.\n\n{BULK_ADD_HINT}"
    )
    return WAITING_FOR_BULK_DATA

async def bulk_add_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    record_type = context.user_data.get('bulk_add_type')
    if record_type not in ('expenses', 'income'):
        await update.message.reply_text("Неизвестный тип. Начни заново командой /cancel и выбери тип.")
        return ConversationHandler.END
    
    entries, errors = _parse_bulk_lines(update.message.text, record_type)
    if not entries:
        await update.message.reply_text(
            "Не удалось обработать ни одной строки.\n" + ("\n".join(errors) if errors else "Проверь формат и попробуй еще раз.")
        )
        return WAITING_FOR_BULK_DATA
    
    user_id = update.effective_user.id
    if record_type == 'expenses':
        inserted = db.add_expenses_bulk(user_id, entries)
    else:
        inserted = db.add_income_bulk(user_id, entries)
    
    response = [
        f"✅ Добавлено записей: {inserted}",
    ]
    if errors:
        response.append("⚠️ Ошибки:")
        response.extend(errors[:5])
        if len(errors) > 5:
            response.append(f"...и еще {len(errors) - 5} ошибок.")
    
    await update.message.reply_text("\n".join(response))
    context.user_data.pop('bulk_add_type', None)
    return ConversationHandler.END

async def bulk_delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Расходы", callback_data="bulk_del_expenses"),
            InlineKeyboardButton("Доходы", callback_data="bulk_del_income")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери, что будем удалять:", reply_markup=reply_markup)
    return WAITING_FOR_BULK_DELETE_TYPE

async def bulk_delete_choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    record_type = update.callback_query.data.replace("bulk_del_", "")
    context.user_data['bulk_delete_type'] = record_type
    user_id = update.effective_user.id
    
    if record_type == 'expenses':
        items = db.get_last_expenses(user_id, limit=20)
        title = "Последние расходы"
    else:
        items = db.get_last_income(user_id, limit=20)
        title = "Последние доходы"
    
    if not items:
        await update.callback_query.edit_message_text("Нет записей для удаления.")
        context.user_data.pop('bulk_delete_type', None)
        return ConversationHandler.END
    
    lines = [f"{title} (укажи ID через пробел/запятую):"]
    for item in items:
        descriptor = item.get('category') or item.get('source')
        date_value = item.get('date')
        date_str = format_date(date_value) if date_value else "Без даты"
        lines.append(
            f"ID {item['id']}: {format_currency(item['amount'])} руб., {descriptor} ({date_str})"
        )
    await update.callback_query.edit_message_text("\n".join(lines))
    return WAITING_FOR_BULK_DELETE_IDS

async def bulk_delete_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    record_type = context.user_data.get('bulk_delete_type')
    if record_type not in ('expenses', 'income'):
        await update.message.reply_text("Неизвестный тип удаления. Начни заново c /cancel.")
        return ConversationHandler.END
    
    raw_ids = update.message.text.replace(',', ' ').split()
    ids = []
    for raw in raw_ids:
        try:
            ids.append(int(raw))
        except ValueError:
            continue
    
    if not ids:
        await update.message.reply_text("Не удалось найти ID в сообщении. Отправь их через пробел или отправь /cancel.")
        return WAITING_FOR_BULK_DELETE_IDS
    
    user_id = update.effective_user.id
    if record_type == 'expenses':
        deleted = db.delete_expenses_bulk(user_id, ids)
    else:
        deleted = db.delete_income_bulk(user_id, ids)
    
    await update.message.reply_text(f"🗑 Удалено записей: {deleted}")
    context.user_data.pop('bulk_delete_type', None)
    return ConversationHandler.END

bulk_add_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📥 Массовое добавление$"), bulk_add_start)],
    states={
        WAITING_FOR_BULK_TYPE: [
            CallbackQueryHandler(bulk_add_choose_type, pattern="^bulk_add_(expenses|income)$")
        ],
        WAITING_FOR_BULK_DATA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, bulk_add_process)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)

bulk_delete_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^🗑 Массовое удаление$"), bulk_delete_start)],
    states={
        WAITING_FOR_BULK_DELETE_TYPE: [
            CallbackQueryHandler(bulk_delete_choose_type, pattern="^bulk_del_(expenses|income)$")
        ],
        WAITING_FOR_BULK_DELETE_IDS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, bulk_delete_process)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)

