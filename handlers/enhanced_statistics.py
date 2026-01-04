"""
Расширенная статистика: 7 дней, диаграмма доходов, сравнение категорий
"""
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from utils import format_currency, format_date
from charts_improved import create_pie_chart, create_bar_chart

db = Database()


async def show_last_7_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать последние 7 дней трат"""
    user_id = update.effective_user.id
    stats = db.get_statistics(user_id, 7)
    
    message = "📝 <b>Последние 7 дней</b>\n\n"
    
    expenses_by_day = {}
    for exp in stats['expenses']:
        date_obj = exp['date']
        if isinstance(date_obj, str):
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        date = date_obj.date()
        
        if date not in expenses_by_day:
            expenses_by_day[date] = []
        expenses_by_day[date].append(exp)
    
    sorted_dates = sorted(expenses_by_day.keys(), reverse=True)
    
    for date in sorted_dates:
        date_str = date.strftime('%d.%m (%a)')
        day_expenses = expenses_by_day[date]
        day_total = sum(e['amount'] for e in day_expenses)
        
        message += f"📅 <b>{date_str}</b> - {format_currency(day_total)} руб.\n"
        
        sorted_expenses = sorted(day_expenses, key=lambda x: x['amount'], reverse=True)[:3]
        for exp in sorted_expenses:
            desc = f" ({exp['description'][:20]}...)" if exp.get('description') and len(exp['description']) > 20 else ""
            message += f"  • {exp['category']}: {format_currency(exp['amount'])} руб.{desc}\n"
        
        message += "\n"
    
    if not sorted_dates:
        message += "Нет трат за последние 7 дней."
    
    await update.message.reply_text(message, parse_mode='HTML')


async def show_7_days_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику за 7 дней"""
    user_id = update.effective_user.id
    stats = db.get_statistics(user_id, 7)
    
    message = "📊 <b>Статистика за 7 дней</b>\n\n"
    
    message += f"💸 Расходы: {format_currency(stats['total_expenses'])} руб.\n"
    message += f"💰 Доходы: {format_currency(stats['total_income'])} руб.\n"
    message += f"💵 Баланс: {format_currency(stats['balance'])} руб.\n\n"
    
    if stats['expenses_count'] > 0:
        avg_daily = stats['total_expenses'] / 7
        message += f"📊 Средние траты в день: {format_currency(avg_daily)} руб.\n"
        message += f"📝 Всего операций: {stats['expenses_count']}\n\n"
    
    if stats['expenses_by_category']:
        message += "🏆 <b>Топ-5 категорий расходов:</b>\n"
        sorted_cats = sorted(stats['expenses_by_category'].items(), 
                           key=lambda x: x[1], reverse=True)[:5]
        
        for i, (cat, amount) in enumerate(sorted_cats, 1):
            percent = (amount / stats['total_expenses'] * 100) if stats['total_expenses'] > 0 else 0
            message += f"{i}. {cat}: {format_currency(amount)} руб. ({percent:.0f}%)\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def show_income_chart_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню диаграммы доходов"""
    keyboard = [
        [
            InlineKeyboardButton("30 дней", callback_data="income_chart_30"),
            InlineKeyboardButton("90 дней", callback_data="income_chart_90")
        ],
        [InlineKeyboardButton("Все время", callback_data="income_chart_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📈 <b>Диаграмма доходов</b>\n\n"
        "Выбери период:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def income_chart_period_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создать диаграмму доходов"""
    await update.callback_query.answer("Генерирую диаграмму...")
    
    period_str = update.callback_query.data.replace("income_chart_", "")
    days = None if period_str == "all" else int(period_str)
    
    user_id = update.effective_user.id
    stats = db.get_statistics(user_id, days)
    
    if not stats['income_by_source']:
        await update.callback_query.edit_message_text(
            "У тебя пока нет доходов за этот период."
        )
        return
    
    period_text = {
        30: "30 дней",
        90: "90 дней",
        None: "все время"
    }.get(days, f"{days} дней")
    
    chart_path = create_pie_chart(
        stats['income_by_source'],
        f"Доходы по источникам ({period_text})"
    )
    
    if not chart_path or not os.path.exists(chart_path):
        await update.callback_query.edit_message_text(
            "Недостаточно данных для диаграммы."
        )
        return
    
    try:
        await update.callback_query.message.reply_photo(
            photo=open(chart_path, 'rb'),
            caption=f"📈 Доходы за {period_text}\n"
                   f"💰 Всего: {format_currency(stats['total_income'])} руб."
        )
        await update.callback_query.message.delete()
    finally:
        if os.path.exists(chart_path):
            os.remove(chart_path)


async def show_category_comparison(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сравнение категорий за последние 2 месяца"""
    user_id = update.effective_user.id
    
    stats_current = db.get_statistics(user_id, 30)
    
    all_expenses = db.get_expenses(user_id, 60)
    cutoff = datetime.now() - timedelta(days=30)
    
    prev_expenses = [e for e in all_expenses 
                    if datetime.fromisoformat(str(e['date']).replace('Z', '+00:00')) < cutoff]
    
    prev_by_category = {}
    for e in prev_expenses:
        cat = e['category']
        prev_by_category[cat] = prev_by_category.get(cat, 0) + e['amount']
    
    all_cats = set(list(stats_current['expenses_by_category'].keys()) + 
                  list(prev_by_category.keys()))
    
    message = "📊 <b>Сравнение категорий</b>\n"
    message += "Текущий месяц vs Прошлый месяц\n\n"
    
    for cat in sorted(all_cats):
        current = stats_current['expenses_by_category'].get(cat, 0)
        previous = prev_by_category.get(cat, 0)
        
        if current == 0 and previous == 0:
            continue
        
        message += f"📂 <b>{cat}</b>\n"
        message += f"  Сейчас: {format_currency(current)} руб.\n"
        message += f"  Было: {format_currency(previous)} руб.\n"
        
        if previous > 0:
            change = ((current - previous) / previous) * 100
            if change > 0:
                message += f"  📈 +{change:.0f}%\n"
            elif change < 0:
                message += f"  📉 {change:.0f}%\n"
            else:
                message += f"  ➡️ Без изменений\n"
        else:
            message += f"  🆕 Новая категория\n"
        
        message += "\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


__all__ = [
    'show_last_7_days',
    'show_7_days_statistics',
    'show_income_chart_menu',
    'income_chart_period_selected',
    'show_category_comparison'
]