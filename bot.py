import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    PreCheckoutQueryHandler, InlineQueryHandler, ChosenInlineResultHandler, filters, ConversationHandler
)
from config import BOT_TOKEN
from config import WAITING_FOR_BULK_DATA, WAITING_FOR_BULK_TYPE

from handlers.common import start, cancel
from handlers.expenses import (
    expense_handler, delete_expense_handler, 
    delete_expense_callback, expense_page_callback
)
from handlers.income import (
    income_handler, delete_income_handler,
    delete_income_callback, income_page_callback
)
from handlers.bulk import bulk_add_handler, bulk_delete_handler
from handlers.search import search_handler
from handlers.statistics import (
    show_statistics_menu, show_last_3_days, show_export_menu,
    show_pdf_export_menu, show_statistics, handle_export,
    handle_pdf_export
)
from handlers.statistics_charts import (
    show_chart_menu_new, chart_type_selected, chart_period_selected,
    chart_filters_conversation, chart_filtered_type_selected
)
from handlers.smart_features import (
    show_smart_tips, show_achievements, show_period_comparison,
    show_expense_forecast, show_budgets_menu, show_budgets_list,
    delete_budget_start, delete_budget_confirm, budget_conversation
)
from handlers.premium import (
    show_premium_info, buy_premium, precheckout_callback,
    successful_payment_callback, show_category_filters,
    filter_conversation, edit_budget_conversation, edit_budget_start,
    remove_filter_start, remove_filter_confirm, clear_all_filters
)
from handlers.inline_mode import (
    inline_query_handler, inline_stats_callback, chosen_inline_result
)
from handlers.group_functions import (
    group_add_expense, group_statistics, group_add_debt,
    group_my_debts, group_settle_debt, group_help
)

from handlers.balance_handlers import (
    show_balance, show_hidden_history, recalculate_balance,
    hidden_balance_conversation
)
from handlers.category_handlers import (
    show_category_menu, list_categories, delete_category_menu,
    delete_category_confirm, view_expenses_by_category,
    category_selected_for_view, show_category_details,
    add_category_conversation
)
from handlers.notification_handlers import (
    show_notification_settings, toggle_notification_setting,
    show_regular_expenses, add_regular_expense_start,
    regular_expense_conversation, disable_regular_expense
)
from handlers.enhanced_statistics import (
    show_last_7_days, show_7_days_statistics,
    show_income_chart_menu, income_chart_period_selected,
    show_category_comparison
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def main():
    if not BOT_TOKEN:
        print("❌ ОШИБКА: Не найден BOT_TOKEN в переменных окружения!")
        print("Создай файл .env и добавь туда: BOT_TOKEN=твой_токен_бота")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))

    application.add_handler(InlineQueryHandler(inline_query_handler))
    application.add_handler(ChosenInlineResultHandler(chosen_inline_result))
    application.add_handler(CallbackQueryHandler(inline_stats_callback, pattern="^inline_stats$"))

    application.add_handler(CommandHandler("group_expense", group_add_expense))
    application.add_handler(CommandHandler("group_stats", group_statistics))
    application.add_handler(CommandHandler("group_debt", group_add_debt))
    application.add_handler(CommandHandler("group_my_debts", group_my_debts))
    application.add_handler(CommandHandler("group_settle", group_settle_debt))
    application.add_handler(CommandHandler("group_help", group_help))
    application.add_handler(MessageHandler(filters.Regex("^⭐ Premium"), show_premium_info))
    application.add_handler(CallbackQueryHandler(show_premium_info, pattern="^show_premium$"))
    application.add_handler(CallbackQueryHandler(buy_premium, pattern="^buy_premium$"))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    application.add_handler(MessageHandler(filters.Regex("^🎯 Фильтры категорий$"), show_category_filters))
    application.add_handler(CallbackQueryHandler(show_category_filters, pattern="^show_filters$"))
    application.add_handler(filter_conversation)
    application.add_handler(CallbackQueryHandler(remove_filter_start, pattern="^remove_filter$"))
    application.add_handler(CallbackQueryHandler(remove_filter_confirm, pattern="^rmfilter_"))
    application.add_handler(CallbackQueryHandler(clear_all_filters, pattern="^clear_filters$"))
    
    application.add_handler(MessageHandler(filters.Regex("^💰 Баланс$"), show_balance))
    application.add_handler(CallbackQueryHandler(show_hidden_history, pattern="^hidden_history$"))
    application.add_handler(CallbackQueryHandler(recalculate_balance, pattern="^balance_recalc$"))
    application.add_handler(hidden_balance_conversation)
    application.add_handler(MessageHandler(filters.Regex("^📂 Категории$"), show_category_menu))
    application.add_handler(add_category_conversation)
    application.add_handler(CallbackQueryHandler(list_categories, pattern="^cat_list_"))
    application.add_handler(CallbackQueryHandler(delete_category_menu, pattern="^cat_delete_menu$"))
    application.add_handler(CallbackQueryHandler(delete_category_confirm, pattern="^del_cat_"))
    application.add_handler(MessageHandler(filters.Regex("^📊 Траты по категориям$"), view_expenses_by_category))
    application.add_handler(CallbackQueryHandler(category_selected_for_view, pattern="^view_cat_"))
    application.add_handler(CallbackQueryHandler(show_category_details, pattern="^cat_period_"))
    
    application.add_handler(MessageHandler(filters.Regex("^🔔 Уведомления$"), show_notification_settings))
    application.add_handler(CallbackQueryHandler(toggle_notification_setting, pattern="^notif_toggle_"))
    application.add_handler(MessageHandler(filters.Regex("^⏰ Регулярные траты$"), show_regular_expenses))
    application.add_handler(regular_expense_conversation)
    application.add_handler(CallbackQueryHandler(disable_regular_expense, pattern="^disable_regular_"))
    
    application.add_handler(MessageHandler(filters.Regex("^📝 Последние 7 дней$"), show_last_7_days))
    application.add_handler(MessageHandler(filters.Regex("^📊 Статистика 7 дней$"), show_7_days_statistics))
    application.add_handler(MessageHandler(filters.Regex("^📈 Диаграмма доходов$"), show_income_chart_menu))
    application.add_handler(CallbackQueryHandler(income_chart_period_selected, pattern="^income_chart_"))
    application.add_handler(MessageHandler(filters.Regex("^📊 Сравнение категорий$"), show_category_comparison))

    application.add_handler(expense_handler)
    application.add_handler(income_handler)
    application.add_handler(delete_expense_handler)
    application.add_handler(expense_page_callback)
    application.add_handler(delete_expense_callback)
    application.add_handler(delete_income_handler)
    application.add_handler(income_page_callback)
    application.add_handler(delete_income_callback)
    
    application.add_handler(bulk_add_handler)
    application.add_handler(bulk_delete_handler)
    application.add_handler(search_handler)
    application.add_handler(MessageHandler(filters.Regex("^💡 Умные советы$"), show_smart_tips))
    application.add_handler(MessageHandler(filters.Regex("^🏆 Достижения$"), show_achievements))
    application.add_handler(MessageHandler(filters.Regex("^📊 Сравнить месяцы$"), show_period_comparison))
    application.add_handler(MessageHandler(filters.Regex("^🔮 Прогноз$"), show_expense_forecast))
    application.add_handler(MessageHandler(filters.Regex("^💰 Бюджеты$"), show_budgets_menu))
    application.add_handler(budget_conversation)
    application.add_handler(edit_budget_conversation)
    application.add_handler(CallbackQueryHandler(show_budgets_list, pattern="^budgets_list$"))
    application.add_handler(CallbackQueryHandler(edit_budget_start, pattern="^budgets_edit$"))
    application.add_handler(CallbackQueryHandler(delete_budget_start, pattern="^budgets_delete$"))
    application.add_handler(CallbackQueryHandler(delete_budget_confirm, pattern="^del_budget_"))
    
    application.add_handler(MessageHandler(filters.Regex("^📊 Статистика$"), show_statistics_menu))
    application.add_handler(MessageHandler(filters.Regex("^📝 Последние 3 дня$"), show_last_3_days))
    application.add_handler(MessageHandler(filters.Regex("^📤 Экспорт$"), show_export_menu))
    application.add_handler(MessageHandler(filters.Regex("^📄 Экспорт PDF$"), show_pdf_export_menu))
    application.add_handler(CallbackQueryHandler(show_statistics, pattern="^stat_"))
    application.add_handler(CallbackQueryHandler(handle_export, pattern="^exp_"))
    application.add_handler(CallbackQueryHandler(handle_pdf_export, pattern="^pdf_"))
    
    application.add_handler(MessageHandler(filters.Regex("^📈 Диаграмма$"), show_chart_menu_new))
    application.add_handler(CallbackQueryHandler(chart_type_selected, pattern="^chart_type_"))
    application.add_handler(CallbackQueryHandler(chart_period_selected, pattern="^chart_period_"))
    application.add_handler(chart_filters_conversation)
    application.add_handler(CallbackQueryHandler(chart_filtered_type_selected, pattern="^chart_filtered_"))
    
    print("=" * 80)
    print("✅ Бот успешно запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()