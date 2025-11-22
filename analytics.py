"""
Модуль умной аналитики и советов
"""
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from database import Database

db = Database()


def get_spending_insights(user_id: int) -> Dict:
    """Получить инсайты о тратах пользователя"""
    stats_30 = db.get_statistics(user_id, 30)
    stats_7 = db.get_statistics(user_id, 7)
    
    insights = {
        'daily_average': 0,
        'weekly_trend': 'stable',
        'top_category': None,
        'top_category_percent': 0,
        'unusual_spending': [],
        'savings_potential': 0
    }
    
    # Средние траты в день
    if stats_30['expenses_count'] > 0:
        insights['daily_average'] = stats_30['total_expenses'] / 30
    
    # Тренд последней недели
    if stats_7['total_expenses'] > 0 and stats_30['total_expenses'] > 0:
        weekly_avg = stats_30['total_expenses'] / 4.3  # ~4.3 недели в месяце
        if stats_7['total_expenses'] > weekly_avg * 1.2:
            insights['weekly_trend'] = 'increasing'
        elif stats_7['total_expenses'] < weekly_avg * 0.8:
            insights['weekly_trend'] = 'decreasing'
    
    # Топ категория
    if stats_30['expenses_by_category']:
        top_cat = max(stats_30['expenses_by_category'].items(), key=lambda x: x[1])
        insights['top_category'] = top_cat[0]
        if stats_30['total_expenses'] > 0:
            insights['top_category_percent'] = (top_cat[1] / stats_30['total_expenses']) * 100
    
    # Необычные траты (больше чем средний чек * 3)
    if stats_30['expenses']:
        avg_expense = stats_30['total_expenses'] / stats_30['expenses_count']
        for exp in stats_30['expenses'][:10]:
            if exp['amount'] > avg_expense * 3:
                insights['unusual_spending'].append({
                    'amount': exp['amount'],
                    'category': exp['category'],
                    'date': exp['date']
                })
    
    # Потенциал для экономии (если баланс отрицательный)
    if stats_30['balance'] < 0:
        insights['savings_potential'] = abs(stats_30['balance']) * 0.2  # 20% от дефицита
    
    return insights


def generate_smart_tips(user_id: int) -> List[str]:
    """Генерировать умные советы на основе анализа"""
    insights = get_spending_insights(user_id)
    stats = db.get_statistics(user_id, 30)
    tips = []
    
    # Совет по балансу
    if stats['balance'] < 0:
        tips.append(
            f"⚠️ Твой баланс отрицательный: {abs(stats['balance']):.0f} руб.\n"
            f"Попробуй сократить расходы на {insights['savings_potential']:.0f} руб."
        )
    elif stats['balance'] > stats['total_expenses'] * 0.3:
        tips.append(
            f"🎉 Отличная работа! У тебя запас в {stats['balance']:.0f} руб.\n"
            "Это больше 30% от месячных расходов!"
        )
    
    # Совет по топ категории
    if insights['top_category'] and insights['top_category_percent'] > 40:
        tips.append(
            f"📊 Категория '{insights['top_category']}' занимает {insights['top_category_percent']:.0f}% расходов.\n"
            "Возможно, стоит обратить внимание на оптимизацию?"
        )
    
    # Совет по тренду
    if insights['weekly_trend'] == 'increasing':
        tips.append(
            "📈 Твои траты выросли на этой неделе.\n"
            f"Средний чек в день: {insights['daily_average']:.0f} руб."
        )
    elif insights['weekly_trend'] == 'decreasing':
        tips.append(
            "📉 Отлично! Траты снижаются.\n"
            "Продолжай в том же духе!"
        )
    
    # Совет по необычным тратам
    if insights['unusual_spending']:
        large_expense = insights['unusual_spending'][0]
        tips.append(
            f"💸 Обнаружена крупная трата: {large_expense['amount']:.0f} руб. на {large_expense['category']}.\n"
            "Это в 3+ раза больше твоего среднего чека!"
        )
    
    # Общие советы
    if stats['expenses_count'] < 10:
        tips.append(
            "💡 Добавь больше операций для более точной аналитики.\n"
            "Рекомендуем записывать все расходы ежедневно!"
        )
    
    if not tips:
        tips.append(
            "✨ Пока нет специальных советов.\n"
            "Продолжай вести учет, и я дам персональные рекомендации!"
        )
    
    return tips


def get_achievements(user_id: int) -> Dict:
    """Получить достижения пользователя"""
    stats_all = db.get_statistics(user_id, None)
    stats_30 = db.get_statistics(user_id, 30)
    
    achievements = []
    
    # Достижение за количество записей
    if stats_all['expenses_count'] + stats_all['income_count'] >= 100:
        achievements.append("🏆 Мастер учета - 100+ операций!")
    elif stats_all['expenses_count'] + stats_all['income_count'] >= 50:
        achievements.append("🥈 Ученик - 50+ операций")
    elif stats_all['expenses_count'] + stats_all['income_count'] >= 10:
        achievements.append("🥉 Новичок - 10+ операций")
    
    # Достижение за положительный баланс
    if stats_30['balance'] > 0:
        achievements.append("💰 В плюсе - положительный баланс!")
    
    # Достижение за регулярность
    if stats_30['expenses_count'] >= 20:
        achievements.append("📊 Дисциплинированный - 20+ записей за месяц")
    
    # Достижение за разнообразие категорий
    if len(stats_30['expenses_by_category']) >= 5:
        achievements.append("🎨 Разносторонний - 5+ категорий трат")
    
    # Достижение за экономию
    if stats_30['total_income'] > 0:
        savings_rate = (stats_30['balance'] / stats_30['total_income']) * 100
        if savings_rate > 30:
            achievements.append(f"🐷 Копилка - экономия {savings_rate:.0f}%")
    
    # Интересные факты
    facts = []
    
    if stats_all['total_expenses'] > 0:
        facts.append(f"💸 Всего потрачено: {stats_all['total_expenses']:,.0f} руб.")
    
    if stats_all['total_income'] > 0:
        facts.append(f"💰 Всего заработано: {stats_all['total_income']:,.0f} руб.")
    
    if stats_30['expenses_by_category']:
        top_cat = max(stats_30['expenses_by_category'].items(), key=lambda x: x[1])
        facts.append(f"🎯 Любимая категория: {top_cat[0]}")
    
    avg_expense = stats_all['total_expenses'] / stats_all['expenses_count'] if stats_all['expenses_count'] > 0 else 0
    if avg_expense > 0:
        facts.append(f"📊 Средний чек: {avg_expense:,.0f} руб.")
    
    return {
        'achievements': achievements,
        'facts': facts,
        'total_operations': stats_all['expenses_count'] + stats_all['income_count']
    }


def compare_periods(user_id: int) -> Dict:
    """Сравнить текущий месяц с предыдущим"""
    # Текущий месяц (последние 30 дней)
    current = db.get_statistics(user_id, 30)
    
    # Предыдущий период (30-60 дней назад)
    expenses_prev = db.get_expenses(user_id, 60)
    income_prev = db.get_income(user_id, 60)
    
    # Фильтруем только операции 30-60 дней назад
    cutoff = datetime.now() - timedelta(days=30)
    
    expenses_prev = [e for e in expenses_prev if datetime.fromisoformat(e['date'].replace('Z', '+00:00')) < cutoff]
    income_prev = [i for i in income_prev if datetime.fromisoformat(i['date'].replace('Z', '+00:00')) < cutoff]
    
    prev_total_expenses = sum(e['amount'] for e in expenses_prev)
    prev_total_income = sum(i['amount'] for i in income_prev)
    prev_balance = prev_total_income - prev_total_expenses
    
    # Вычисляем изменения
    expenses_change = 0
    income_change = 0
    balance_change = 0
    
    if prev_total_expenses > 0:
        expenses_change = ((current['total_expenses'] - prev_total_expenses) / prev_total_expenses) * 100
    
    if prev_total_income > 0:
        income_change = ((current['total_income'] - prev_total_income) / prev_total_income) * 100
    
    if prev_balance != 0:
        balance_change = current['balance'] - prev_balance
    
    return {
        'current': current,
        'previous': {
            'total_expenses': prev_total_expenses,
            'total_income': prev_total_income,
            'balance': prev_balance
        },
        'changes': {
            'expenses': expenses_change,
            'income': income_change,
            'balance': balance_change
        }
    }


def predict_monthly_expenses(user_id: int) -> Dict:
    """Предсказать расходы на конец месяца"""
    stats_7 = db.get_statistics(user_id, 7)
    stats_30 = db.get_statistics(user_id, 30)
    
    # Текущий день месяца
    current_day = datetime.now().day
    days_in_month = 30  # Упрощение
    
    # Прогноз на основе последней недели
    weekly_avg = stats_7['total_expenses']
    weeks_remaining = (days_in_month - current_day) / 7
    predicted_from_week = stats_30['total_expenses'] + (weekly_avg * weeks_remaining)
    
    # Прогноз на основе среднего дневного
    if current_day > 0:
        daily_avg = stats_30['total_expenses'] / current_day
        predicted_from_daily = daily_avg * days_in_month
    else:
        predicted_from_daily = predicted_from_week
    
    # Среднее между двумя прогнозами
    prediction = (predicted_from_week + predicted_from_daily) / 2
    
    return {
        'current_expenses': stats_30['total_expenses'],
        'predicted_total': prediction,
        'predicted_remaining': prediction - stats_30['total_expenses'],
        'daily_average': stats_30['total_expenses'] / max(current_day, 1),
        'days_passed': current_day,
        'days_remaining': days_in_month - current_day
    }