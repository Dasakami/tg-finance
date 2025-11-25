import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from utils import format_currency
from export import export_to_excel, export_to_pdf
from charts import create_statistics_chart

logger = logging.getLogger(__name__)
db = Database()


async def show_statistics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Вчера", callback_data="stat_1"),
            InlineKeyboardButton("3 дня", callback_data="stat_3")
        ],
        [
            InlineKeyboardButton("15 дней", callback_data="stat_15"),
            InlineKeyboardButton("30 дней", callback_data="stat_30")
        ],
        [
            InlineKeyboardButton("90 дней", callback_data="stat_90"),
            InlineKeyboardButton("Все время", callback_data="stat_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери период для просмотра статистики:", reply_markup=reply_markup)


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    days_str = update.callback_query.data.replace("stat_", "")
    days = None if days_str == "all" else int(days_str)
    user_id = update.effective_user.id
    stats = db.get_statistics(user_id, days)
    
    period_name = {
        1: "Вчера",
        3: "Последние 3 дня",
        15: "Последние 15 дней",
        30: "Последние 30 дней",
        90: "Последние 90 дней",
        None: "Все время"
    }.get(days, f"{days} дней")
    
    text = f"📊 Статистика за {period_name}\n\n"
    text += f"💰 Доходы: {format_currency(stats['total_income'])} руб.\n"
    text += f"💸 Расходы: {format_currency(stats['total_expenses'])} руб.\n"
    text += f"💵 Баланс: {format_currency(stats['balance'])} руб.\n\n"
    
    if stats['expenses_by_category']:
        text += "📂 Расходы по категориям:\n"
        for cat, amount in sorted(stats['expenses_by_category'].items(), key=lambda x: x[1], reverse=True)[:5]:
            text += f"  • {cat}: {format_currency(amount)} руб.\n"
        text += "\n"
    
    if stats['income_by_source']:
        text += "📈 Доходы по источникам:\n"
        for src, amount in sorted(stats['income_by_source'].items(), key=lambda x: x[1], reverse=True)[:5]:
            text += f"  • {src}: {format_currency(amount)} руб.\n"
    
    await update.callback_query.message.reply_text(text)


async def show_last_3_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_statistics(user_id, 3)
    text = "📝 Последние 3 дня\n\n"
    
    expenses_by_day = {}
    income_by_day = {}
    
    for exp in stats['expenses']:
        date_obj = exp['date']
        if isinstance(date_obj, str):
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        date = date_obj.date()
        if date not in expenses_by_day:
            expenses_by_day[date] = []
        expenses_by_day[date].append(exp)
    
    for inc in stats['income']:
        date_obj = inc['date']
        if isinstance(date_obj, str):
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        date = date_obj.date()
        if date not in income_by_day:
            income_by_day[date] = []
        income_by_day[date].append(inc)
    
    all_dates = sorted(set(list(expenses_by_day.keys()) + list(income_by_day.keys())), reverse=True)
    
    for date in all_dates[:3]:
        date_str = date.strftime('%d.%m.%Y')
        text += f"📅 {date_str}\n"
        
        if date in expenses_by_day:
            text += "  💸 Расходы:\n"
            for exp in expenses_by_day[date][:5]:
                desc = f" - {exp['description']}" if exp['description'] else ""
                text += f"    • {exp['category']}: {format_currency(exp['amount'])} руб.{desc}\n"
        
        if date in income_by_day:
            text += "  💰 Доходы:\n"
            for inc in income_by_day[date][:5]:
                desc = f" - {inc['description']}" if inc['description'] else ""
                text += f"    • {inc['source']}: {format_currency(inc['amount'])} руб.{desc}\n"
        
        text += "\n"
    
    if not text.strip() or text == "📝 Последние 3 дня\n\n":
        text += "Нет данных за последние 3 дня."
    
    await update.message.reply_text(text)


async def show_export_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("5 дней", callback_data="exp_5"),
            InlineKeyboardButton("15 дней", callback_data="exp_15"),
            InlineKeyboardButton("30 дней", callback_data="exp_30")
        ],
        [
            InlineKeyboardButton("60 дней", callback_data="exp_60"),
            InlineKeyboardButton("90 дней", callback_data="exp_90")
        ],
        [
            InlineKeyboardButton("Все время", callback_data="exp_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери период для экспорта:", reply_markup=reply_markup)


async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    
    # Исправление: правильно парсим callback_data
    callback_data = update.callback_query.data
    days_str = callback_data.replace("exp_", "")
    
    # Преобразуем в int или None
    if days_str == "all":
        days = None
        period_text = "все время"
    else:
        try:
            days = int(days_str)
            period_text = f"{days} дней"
        except ValueError:
            await update.callback_query.message.reply_text("❌ Ошибка: неверный формат периода")
            return
    
    user_id = update.effective_user.id
    
    try:
        file_path = export_to_excel(db, user_id, days)
        
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as file:
                await update.callback_query.message.reply_document(
                    document=file,
                    filename=f"finance_export_{period_text.replace(' ', '_')}.xlsx",
                    caption=f"📤 Экспорт данных за {period_text}"
                )
            
            # Удаляем файл после отправки
            try:
                os.remove(file_path)
            except:
                pass
        else:
            await update.callback_query.message.reply_text("❌ Ошибка при создании файла экспорта.")
            
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        await update.callback_query.message.reply_text(
            "❌ Произошла ошибка при экспорте данных.\n"
            f"Детали: {str(e)}"
        )


async def show_pdf_export_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("5 дней", callback_data="pdf_5"),
            InlineKeyboardButton("15 дней", callback_data="pdf_15"),
            InlineKeyboardButton("30 дней", callback_data="pdf_30")
        ],
        [
            InlineKeyboardButton("60 дней", callback_data="pdf_60"),
            InlineKeyboardButton("90 дней", callback_data="pdf_90")
        ],
        [
            InlineKeyboardButton("Все время", callback_data="pdf_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери период для PDF-отчета:", reply_markup=reply_markup)


async def handle_pdf_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    
    # Исправление: правильно парсим callback_data
    callback_data = update.callback_query.data
    days_str = callback_data.replace("pdf_", "")
    
    # Преобразуем в int или None
    if days_str == "all":
        days = None
        period_text = "все время"
    else:
        try:
            days = int(days_str)
            period_text = f"{days} дней"
        except ValueError:
            await update.callback_query.message.reply_text("❌ Ошибка: неверный формат периода")
            return
    
    user_id = update.effective_user.id
    
    try:
        file_path = export_to_pdf(db, user_id, days)
        
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as file:
                await update.callback_query.message.reply_document(
                    document=file,
                    filename=f"finance_report_{period_text.replace(' ', '_')}.pdf",
                    caption=f"📄 PDF-отчет за {period_text}"
                )
            
            # Удаляем файл после отправки
            try:
                os.remove(file_path)
            except:
                pass
        else:
            await update.callback_query.message.reply_text("❌ Ошибка при создании PDF.")
            
    except Exception as e:
        logger.error(f"PDF export error: {e}", exc_info=True)
        await update.callback_query.message.reply_text(
            "❌ Произошла ошибка при создании PDF.\n"
            f"Детали: {str(e)}"
        )


async def show_chart_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню выбора периода для диаграммы"""
    keyboard = [
        [
            InlineKeyboardButton("30 дней", callback_data="chart_30"),
            InlineKeyboardButton("90 дней", callback_data="chart_90")
        ],
        [
            InlineKeyboardButton("Все время", callback_data="chart_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери период для диаграммы:", reply_markup=reply_markup)


async def send_statistics_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка диаграммы (для обратной совместимости - 30 дней)"""
    # Если вызвано через кнопку меню, показываем меню выбора периода
    if update.message:
        await show_chart_menu(update, context)


async def handle_chart_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка генерации диаграммы за выбранный период"""
    await update.callback_query.answer()
    
    # Исправление: правильно парсим callback_data
    callback_data = update.callback_query.data
    days_str = callback_data.replace("chart_", "")
    
    # Преобразуем в int или None
    if days_str == "all":
        days = None
        period_text = "все время"
    else:
        try:
            days = int(days_str)
            period_text = f"{days} дней"
        except ValueError:
            await update.callback_query.message.reply_text("❌ Ошибка: неверный формат периода")
            return
    
    user_id = update.effective_user.id
    
    try:
        stats = db.get_statistics(user_id, days)
        chart_path = create_statistics_chart(stats, period_text)
        
        if not chart_path or not os.path.exists(chart_path):
            await update.callback_query.message.reply_text("Недостаточно данных для построения диаграммы.")
            return
        
        with open(chart_path, 'rb') as photo:
            await update.callback_query.message.reply_photo(
                photo=photo,
                caption=f"📈 Диаграмма расходов/доходов за {period_text}"
            )
        
        # Удаляем файл после отправки
        try:
            os.remove(chart_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Chart generation error: {e}", exc_info=True)
        await update.callback_query.message.reply_text(
            "❌ Произошла ошибка при создании диаграммы.\n"
            f"Детали: {str(e)}"
        )


__all__ = [
    'show_statistics_menu',
    'show_last_3_days',
    'show_export_menu',
    'show_pdf_export_menu',
    'show_statistics',
    'handle_export',
    'handle_pdf_export',
    'send_statistics_chart',
    'show_chart_menu',
    'handle_chart_generation'
]