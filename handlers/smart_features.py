"""
Обновленные обработчики для умных функций с поддержкой фильтров
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from budgets import budget_manager
from utils import format_currency, format_date
from handlers.common import cancel
from config import BACK_BUTTON_TEXT
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')
try:
    from analytics import (
        generate_smart_tips, get_achievements, compare_periods,
        predict_monthly_expenses
    )
except ImportError:
    from analytics import (
        generate_smart_tips, get_achievements, compare_periods,
        predict_monthly_expenses
    )

WAITING_FOR_BUDGET_CATEGORY = 100
WAITING_FOR_BUDGET_AMOUNT = 101


async def show_smart_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать умные советы"""
    user_id = update.effective_user.id
    tips = generate_smart_tips(user_id)
    
    message = "💡 <b>Умные советы и аналитика</b>\n\n"
    
    for i, tip in enumerate(tips, 1):
        message += f"{i}. {tip}\n\n"
    
    try:
        from subscription import subscription_manager
        if subscription_manager.is_premium(user_id):
            message += "\n🎯 <i>Используй фильтры категорий для точной аналитики</i>"
        else:
            message += "\n⭐ <i>Premium: фильтруй категории для точного анализа</i>"
    except:
        pass
    
    await update.message.reply_text(message, parse_mode='HTML')


async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_achievements(user_id)
    
    message = "🏆 <b>Твои достижения</b>\n\n"
    
    if data['achievements']:
        for achievement in data['achievements']:
            message += f"{achievement}\n"
    else:
        message += "Пока нет достижений. Продолжай вести учет!\n"
    
    message += f"\n📊 <b>Интересные факты:</b>\n\n"
    
    for fact in data['facts']:
        message += f"{fact}\n"
    
    message += f"\n<b>Всего операций:</b> {data['total_operations']}"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def show_period_comparison(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать сравнение текущего и предыдущего периода"""
    user_id = update.effective_user.id
    comparison = compare_periods(user_id)
    
    current = comparison['current']
    previous = comparison['previous']
    changes = comparison['changes']
    filters_applied = comparison.get('filters_applied', False)
    
    message = "📊 <b>Сравнение месяцев</b>\n\n"
    
    if filters_applied:
        message += "🎯 <i>Применены фильтры категорий</i>\n\n"
    
    message += "💰 <b>ДОХОДЫ</b>\n"
    message += f"Текущий месяц: {format_currency(current['total_income'])} руб.\n"
    message += f"Прошлый месяц: {format_currency(previous['total_income'])} руб.\n"
    
    if changes['income'] > 0:
        message += f"📈 +{changes['income']:.1f}%\n\n"
    elif changes['income'] < 0:
        message += f"📉 {changes['income']:.1f}%\n\n"
    else:
        message += "➡️ Без изменений\n\n"
    
    message += "💸 <b>РАСХОДЫ</b>\n"
    message += f"Текущий месяц: {format_currency(current['total_expenses'])} руб.\n"
    message += f"Прошлый месяц: {format_currency(previous['total_expenses'])} руб.\n"
    
    if changes['expenses'] > 0:
        message += f"📈 +{changes['expenses']:.1f}%\n\n"
    elif changes['expenses'] < 0:
        message += f"📉 {changes['expenses']:.1f}%\n\n"
    else:
        message += "➡️ Без изменений\n\n"
    
    message += "💵 <b>БАЛАНС</b>\n"
    message += f"Текущий: {format_currency(current['balance'])} руб.\n"
    message += f"Прошлый: {format_currency(previous['balance'])} руб.\n"
    
    if changes['balance'] > 0:
        message += f"✅ Улучшение на {format_currency(changes['balance'])} руб."
    elif changes['balance'] < 0:
        message += f"⚠️ Ухудшение на {format_currency(abs(changes['balance']))} руб."
    else:
        message += "➡️ Без изменений"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def show_expense_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать прогноз расходов"""
    user_id = update.effective_user.id
    forecast = predict_monthly_expenses(user_id)
    filters_applied = forecast.get('filters_applied', False)
    
    message = "🔮 <b>Прогноз расходов на месяц</b>\n\n"
    
    if filters_applied:
        message += "🎯 <i>Применены фильтры категорий</i>\n\n"
    
    message += f"📅 Прошло дней: {forecast['days_passed']}\n"
    message += f"📅 Осталось дней: {forecast['days_remaining']}\n\n"
    
    message += f"💸 Потрачено: {format_currency(forecast['current_expenses'])} руб.\n"
    message += f"📊 В день: {format_currency(forecast['daily_average'])} руб.\n\n"
    
    message += f"🎯 <b>Прогноз на конец месяца:</b>\n"
    message += f"Всего: {format_currency(forecast['predicted_total'])} руб.\n"
    message += f"Осталось потратить: {format_currency(forecast['predicted_remaining'])} руб.\n\n"
    
    if forecast['predicted_remaining'] > 0:
        daily_budget = forecast['predicted_remaining'] / max(forecast['days_remaining'], 1)
        message += f"💡 Дневной бюджет: {format_currency(daily_budget)} руб."
    else:
        message += "⚠️ Прогноз показывает превышение!"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def show_budgets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню бюджетов"""
    user_id = update.effective_user.id
    try:
        from subscription import subscription_manager
        is_premium = subscription_manager.is_premium(user_id)
    except:
        is_premium = False
    
    keyboard = [
        [InlineKeyboardButton("📋 Мои бюджеты", callback_data="budgets_list")],
        [InlineKeyboardButton("➕ Добавить бюджет", callback_data="budgets_add")]
    ]
    
    if is_premium:
        keyboard.append([InlineKeyboardButton("✏️ Редактировать бюджет", callback_data="budgets_edit")])
    
    keyboard.append([InlineKeyboardButton("🗑 Удалить бюджет", callback_data="budgets_delete")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    premium_note = "\n⭐ <i>Premium: доступно редактирование</i>" if is_premium else "\n🔒 <i>Редактирование - Premium функция</i>"
    
    await update.message.reply_text(
        "💰 <b>Управление бюджетами</b>\n\n"
        "Установи лимиты трат по категориям и получай уведомления при их превышении!" + premium_note,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def show_budgets_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список бюджетов"""
    await update.callback_query.answer()
    user_id = update.effective_user.id
    
    summary = budget_manager.get_budget_summary(user_id)
    
    if summary['budgets_count'] == 0:
        await update.callback_query.edit_message_text(
            "У тебя пока нет установленных бюджетов.\n"
            "Используй кнопку меню '💰 Бюджеты' чтобы добавить!"
        )
        return
    
    message = "💰 <b>Твои бюджеты за месяц</b>\n\n"
    
    message += f"<b>Общий лимит:</b> {format_currency(summary['total_budget'])} руб.\n"
    message += f"<b>Потрачено:</b> {format_currency(summary['total_spent'])} руб.\n"
    message += f"<b>Осталось:</b> {format_currency(summary['total_remaining'])} руб.\n\n"
    
    if summary['exceeded']:
        message += "🔴 <b>Превышены:</b>\n"
        for b in summary['exceeded']:
            message += f"  • {b['category']}: {format_currency(b['spent'])} / {format_currency(b['limit_amount'])} руб. ({b['percent_used']:.0f}%)\n"
        message += "\n"
    
    if summary['warning']:
        message += "🟡 <b>Предупреждение:</b>\n"
        for b in summary['warning']:
            message += f"  • {b['category']}: {format_currency(b['spent'])} / {format_currency(b['limit_amount'])} руб. ({b['percent_used']:.0f}%)\n"
        message += "\n"
    
    if summary['safe']:
        message += "🟢 <b>В пределах нормы:</b>\n"
        for b in summary['safe']:
            message += f"  • {b['category']}: {format_currency(b['spent'])} / {format_currency(b['limit_amount'])} руб. ({b['percent_used']:.0f}%)\n"
    
    await update.callback_query.edit_message_text(message, parse_mode='HTML')


async def add_budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления бюджета"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "Введи название категории для бюджета\n"
        "(например: Еда, Транспорт, Развлечения):"
    )
    return WAITING_FOR_BUDGET_CATEGORY


async def add_budget_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить категорию для бюджета"""
    category = update.message.text
    context.user_data['budget_category'] = category
    
    await update.message.reply_text(
        f"Категория: {category}\n\n"
        "Теперь введи месячный лимит в рублях:"
    )
    return WAITING_FOR_BUDGET_AMOUNT


async def add_budget_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить бюджет"""
    try:
        amount = float(update.message.text.replace(',', '.'))
        if amount <= 0:
            await update.message.reply_text("Сумма должна быть положительной!")
            return WAITING_FOR_BUDGET_AMOUNT
        
        user_id = update.effective_user.id
        category = context.user_data['budget_category']
        
        success = budget_manager.set_budget(user_id, category, amount)
        
        if success:
            await update.message.reply_text(
                f"✅ Бюджет установлен!\n\n"
                f"📂 Категория: {category}\n"
                f"💰 Лимит: {format_currency(amount)} руб./месяц"
            )
        else:
            await update.message.reply_text("❌ Ошибка при сохранении бюджета.")
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи число:")
        return WAITING_FOR_BUDGET_AMOUNT


async def delete_budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список бюджетов для удаления"""
    await update.callback_query.answer()
    user_id = update.effective_user.id
    budgets = budget_manager.get_budgets(user_id)
    
    if not budgets:
        await update.callback_query.edit_message_text("У тебя нет бюджетов для удаления.")
        return
    
    buttons = []
    for budget in budgets:
        buttons.append([
            InlineKeyboardButton(
                f"{budget['category']} ({format_currency(budget['limit_amount'])} руб.)",
                callback_data=f"del_budget_{budget['category']}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.callback_query.edit_message_text(
        "Выбери бюджет для удаления:",
        reply_markup=reply_markup
    )


async def delete_budget_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтвердить удаление бюджета"""
    await update.callback_query.answer()
    category = update.callback_query.data.replace("del_budget_", "")
    user_id = update.effective_user.id
    
    success = budget_manager.delete_budget(user_id, category)
    
    if success:
        await update.callback_query.edit_message_text(f"✅ Бюджет '{category}' удален.")
    else:
        await update.callback_query.edit_message_text("❌ Не удалось удалить бюджет.")

budget_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_budget_start, pattern="^budgets_add$")],
    states={
        WAITING_FOR_BUDGET_CATEGORY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_budget_category)
        ],
        WAITING_FOR_BUDGET_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_budget_amount)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), cancel)
    ]
)


__all__ = [
    'show_smart_tips',
    'show_achievements',
    'show_period_comparison',
    'show_expense_forecast',
    'show_budgets_menu',
    'show_budgets_list',
    'delete_budget_start',
    'delete_budget_confirm',
    'budget_conversation'
]