import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    PreCheckoutQueryHandler, InlineQueryHandler, ChosenInlineResultHandler, filters
)
from config import BOT_TOKEN
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
    
    print("=" * 60)
    print("✅ Бот успешно запущен!")
    print("=" * 60)
    print("🎯 Активные функции:")
    print("  ✓ Учет расходов и доходов")
    print("  ✓ Статистика и диаграммы (3 типа)")
    print("  ✓ Экспорт в Excel и PDF")
    print("  ✓ Умные советы и аналитика")
    print("=" * 60)
    print("⭐ Premium функции:")
    print("  ✓ Редактирование бюджетов")
    print("  ✓ Фильтрация категорий")
    print("  ✓ Диаграммы с фильтрами")
    print("  💎 Стоимость: 1 Telegram Star = 1 месяц")
    print("=" * 60)
    print("🤖 Inline режим:")
    print("  ✓ @bot расход 500 еда")
    print("  ✓ @bot доход 5000 зарплата")
    print("=" * 60)
    print("👥 Групповые функции:")
    print("  ✓ /group_expense - добавить групповой расход")
    print("  ✓ /group_stats - статистика группы")
    print("  ✓ /group_debt - учет долгов")
    print("  ✓ /group_my_debts - мои долги")
    print("=" * 60)
    print("📊 Типы диаграмм:")
    print("  • Круговая (с легендой в углу)")
    print("  • Столбчатая")
    print("  • Линейная")
    print("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()