import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters
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
    handle_pdf_export, send_statistics_chart,
    show_chart_menu, handle_chart_generation
)
from handlers.smart_features import (
    show_smart_tips, show_achievements, show_period_comparison,
    show_expense_forecast, show_budgets_menu, show_budgets_list,
    delete_budget_start, delete_budget_confirm, budget_conversation
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    if not BOT_TOKEN:
        print("ОШИБКА: Не найден BOT_TOKEN в переменных окружения!")
        print("Создай файл .env и добавь туда: BOT_TOKEN=твой_токен_бота")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    
    # Обработчики расходов и доходов
    application.add_handler(expense_handler)
    application.add_handler(income_handler)
    
    # Обработчики удаления с пагинацией
    application.add_handler(delete_expense_handler)
    application.add_handler(expense_page_callback)
    application.add_handler(delete_expense_callback)
    
    application.add_handler(delete_income_handler)
    application.add_handler(income_page_callback)
    application.add_handler(delete_income_callback)
    
    # Массовые операции
    application.add_handler(bulk_add_handler)
    application.add_handler(bulk_delete_handler)
    
    # Поиск
    application.add_handler(search_handler)
    
    # Умные функции
    application.add_handler(MessageHandler(filters.Regex("^💡 Умные советы$"), show_smart_tips))
    application.add_handler(MessageHandler(filters.Regex("^🏆 Достижения$"), show_achievements))
    application.add_handler(MessageHandler(filters.Regex("^📊 Сравнить месяцы$"), show_period_comparison))
    application.add_handler(MessageHandler(filters.Regex("^🔮 Прогноз$"), show_expense_forecast))
    
    # Бюджеты
    application.add_handler(MessageHandler(filters.Regex("^💰 Бюджеты$"), show_budgets_menu))
    application.add_handler(budget_conversation)
    application.add_handler(CallbackQueryHandler(show_budgets_list, pattern="^budgets_list$"))
    application.add_handler(CallbackQueryHandler(delete_budget_start, pattern="^budgets_delete$"))
    application.add_handler(CallbackQueryHandler(delete_budget_confirm, pattern="^del_budget_"))
    
    # Статистика и отчеты
    application.add_handler(MessageHandler(filters.Regex("^📊 Статистика$"), show_statistics_menu))
    application.add_handler(MessageHandler(filters.Regex("^📈 Диаграмма$"), send_statistics_chart))
    application.add_handler(MessageHandler(filters.Regex("^📝 Последние 3 дня$"), show_last_3_days))
    application.add_handler(MessageHandler(filters.Regex("^📤 Экспорт$"), show_export_menu))
    application.add_handler(MessageHandler(filters.Regex("^📄 Экспорт PDF$"), show_pdf_export_menu))
    
    # Callback обработчики
    application.add_handler(CallbackQueryHandler(show_statistics, pattern="^stat_"))
    application.add_handler(CallbackQueryHandler(handle_export, pattern="^exp_"))
    application.add_handler(CallbackQueryHandler(handle_pdf_export, pattern="^pdf_"))
    application.add_handler(CallbackQueryHandler(handle_chart_generation, pattern="^chart_"))
    
    print("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()