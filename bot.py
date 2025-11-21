import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters
)
from config import BOT_TOKEN
from handlers import (
    start, cancel,
    expense_handler, income_handler,
    delete_expense_handler, delete_expense_callback,
    delete_income_handler, delete_income_callback,
    bulk_add_handler, bulk_delete_handler,
    show_statistics_menu, show_last_3_days, show_export_menu,
    show_pdf_export_menu, show_statistics, handle_export,
    handle_pdf_export, send_statistics_chart,
    search_handler
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
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(expense_handler)
    application.add_handler(income_handler)
    application.add_handler(delete_expense_handler)
    application.add_handler(delete_income_handler)
    application.add_handler(bulk_add_handler)
    application.add_handler(bulk_delete_handler)
    application.add_handler(search_handler)
    application.add_handler(MessageHandler(filters.Regex("^📊 Статистика$"), show_statistics_menu))
    application.add_handler(MessageHandler(filters.Regex("^📈 Диаграмма$"), send_statistics_chart))
    application.add_handler(MessageHandler(filters.Regex("^📝 Последние 3 дня$"), show_last_3_days))
    application.add_handler(MessageHandler(filters.Regex("^📤 Экспорт$"), show_export_menu))
    application.add_handler(MessageHandler(filters.Regex("^📄 Экспорт PDF$"), show_pdf_export_menu))
    application.add_handler(CallbackQueryHandler(show_statistics, pattern="^stat_"))
    application.add_handler(CallbackQueryHandler(handle_export, pattern="^exp_"))
    application.add_handler(CallbackQueryHandler(handle_pdf_export, pattern="^pdf_"))
    application.add_handler(delete_expense_callback)
    application.add_handler(delete_income_callback)
    
    print("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
