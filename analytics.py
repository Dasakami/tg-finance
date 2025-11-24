"""
Модуль умной аналитики с поддержкой фильтров категорий
"""
from datetime import datetime, timedelta
from typing import Dict, List
from database import Database

db = Database()


def apply_category_filters(user_id: int, expenses_by_category: Dict, 
                          income_by_source: Dict = None) -> tuple:
    """
    Применить фильтры категорий (Premium функция)
    
    Возвращает: (filtered_expenses, filtered_income, filters_applied)
    """
    try:
        from subscription import subscription_manager
        from category_filter import category_filter
        
        # Проверяем Premium
        if not subscription_manager.is_premium(user_id):
            return expenses_by_category, income_by_source, False
        
        # Применяем фильтры
        filtered_expenses = category_filter.apply_filters(user_id, expenses_by_category, 'expense')
        filtered_income = income_by_source
        
        if income_by_source:
            filtered_income = category_filter.apply_filters(user_id, income_by_source, 'income')
        
        # Проверяем, были ли применены фильтры
        filters_applied = (filtered_expenses != expenses_by_category) or \
                         (income_by_source and filtered_income != income_by_source)
        
        return filtered_expenses, filtered_income, filters_applied
        
    except ImportError:
        # Если модули не доступны, возвращаем без фильтров
        return expenses_by_category, income_by_source, False


def get_spending_insights(user_id: int, use_filters: bool = True) -> Dict:
    """Получить инсайты о тратах пользователя"""
    stats_30 = db.get_statistics(user_id, 30)
    stats_7 = db.get_statistics(user_id, 7)
    
    # Применяем фильтры если Premium
    if use_filters:
        filtered_exp_30, _, filters_applied = apply_category_filters(
            user_id, stats_30['expenses_by_category']
        )
        filtered_exp_7, _, _ = apply_category_filters(
            user_id, stats_7['expenses_by_category']
        )
    else:
        filtered_exp_30 = stats_30['expenses_by_category']
        filtered_exp_7 = stats_7['expenses_by_category']
        filters_applied = False
    
    # Пересчитываем суммы с учетом фильтров
    total_expenses_30 = sum(filtered_exp_30.values())
    total_expenses_7 = sum(filtered_exp_7.values())
    
    insights = {
        'daily_average': 0,
        'weekly_trend': 'stable',
        'top_category': None,
        'top_category_percent': 0,
        'unusual_spending': [],
        'savings_potential': 0,
        'filters_applied': filters_applied
    }
    
    # Средние траты в день
    if stats_30['expenses_count'] > 0 and total_expenses_30 > 0:
        insights['daily_average'] = total_expenses_30 / 30
    
    # Тренд последней недели
    if total_expenses_7 > 0 and total_expenses_30 > 0:
        weekly_avg = total_expenses_30 / 4.3
        if total_expenses_7 > weekly_avg * 1.2:
            insights['weekly_trend'] = 'increasing'
        elif total_expenses_7 < weekly_avg * 0.8:
            insights['weekly_trend'] = 'decreasing'
    
    # Топ категория
    if filtered_exp_30:
        top_cat = max(filtered_exp_30.items(), key=lambda x: x[1])
        insights['top_category'] = top_cat[0]
        if total_expenses_30 > 0:
            insights['top_category_percent'] = (top_cat[1] / total_expenses_30) * 100
    
    # Необычные траты
    if stats_30['expenses'] and total_expenses_30 > 0:
        avg_expense = total_expenses_30 / stats_30['expenses_count']
        for exp in stats_30['expenses'][:10]:
            # Проверяем, не исключена ли категория
            if use_filters and exp['category'] not in filtered_exp_30:
                continue
            if exp['amount'] > avg_expense * 3:
                insights['unusual_spending'].append({
                    'amount': exp['amount'],
                    'category': exp['category'],
                    'date': exp['date']
                })
    
    # Потенциал для экономии
    balance = stats_30['total_income'] - total_expenses_30
    if balance < 0:
        insights['savings_potential'] = abs(balance) * 0.2
    
    return insights


def generate_smart_tips(user_id: int) -> List[str]:
    """Генерировать умные советы на основе анализа"""
    insights = get_spending_insights(user_id, use_filters=True)
    stats = db.get_statistics(user_id, 30)
    
    # Применяем фильтры
    filtered_exp, _, filters_applied = apply_category_filters(
        user_id, stats['expenses_by_category']
    )
    total_expenses = sum(filtered_exp.values())
    
    tips = []
    
    # Уведомление о фильтрах
    if filters_applied:
        tips.append(
            "🎯 <b>Фильтры активны</b>\n"
            "Анализ учитывает только выбранные категории."
        )
    
    # Совет по балансу
    balance = stats['total_income'] - total_expenses
    if balance < 0:
        tips.append(
            f"⚠️ Твой баланс отрицательный: {abs(balance):.0f} руб.\n"
            f"Попробуй сократить расходы на {insights['savings_potential']:.0f} руб."
        )
    elif balance > total_expenses * 0.3:
        tips.append(
            f"🎉 Отличная работа! У тебя запас в {balance:.0f} руб.\n"
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


def predict_monthly_expenses(user_id: int) -> Dict:
    """Предсказать расходы на конец месяца с учетом фильтров"""
    stats_7 = db.get_statistics(user_id, 7)
    stats_30 = db.get_statistics(user_id, 30)
    
    # Применяем фильтры
    filtered_exp_7, _, filters_applied = apply_category_filters(
        user_id, stats_7['expenses_by_category']
    )
    filtered_exp_30, _, _ = apply_category_filters(
        user_id, stats_30['expenses_by_category']
    )
    
    total_expenses_7 = sum(filtered_exp_7.values())
    total_expenses_30 = sum(filtered_exp_30.values())
    
    current_day = datetime.now().day
    days_in_month = 30
    
    # Прогноз на основе последней недели
    weekly_avg = total_expenses_7
    weeks_remaining = (days_in_month - current_day) / 7
    predicted_from_week = total_expenses_30 + (weekly_avg * weeks_remaining)
    
    # Прогноз на основе среднего дневного
    if current_day > 0:
        daily_avg = total_expenses_30 / current_day
        predicted_from_daily = daily_avg * days_in_month
    else:
        predicted_from_daily = predicted_from_week
    
    prediction = (predicted_from_week + predicted_from_daily) / 2
    
    return {
        'current_expenses': total_expenses_30,
        'predicted_total': prediction,
        'predicted_remaining': prediction - total_expenses_30,
        'daily_average': total_expenses_30 / max(current_day, 1),
        'days_passed': current_day,
        'days_remaining': days_in_month - current_day,
        'filters_applied': filters_applied
    }


def compare_periods(user_id: int) -> Dict:
    """Сравнить текущий месяц с предыдущим с учетом фильтров"""
    current = db.get_statistics(user_id, 30)
    
    # Применяем фильтры к текущему периоду
    filtered_exp_curr, filtered_inc_curr, filters_applied = apply_category_filters(
        user_id, current['expenses_by_category'], current['income_by_source']
    )
    
    # Предыдущий период
    expenses_prev = db.get_expenses(user_id, 60)
    income_prev = db.get_income(user_id, 60)
    
    cutoff = datetime.now() - timedelta(days=30)
    
    expenses_prev = [e for e in expenses_prev if datetime.fromisoformat(e['date'].replace('Z', '+00:00')) < cutoff]
    income_prev = [i for i in income_prev if datetime.fromisoformat(i['date'].replace('Z', '+00:00')) < cutoff]
    
    # Группируем предыдущий период
    prev_exp_by_cat = {}
    for e in expenses_prev:
        cat = e['category']
        prev_exp_by_cat[cat] = prev_exp_by_cat.get(cat, 0) + e['amount']
    
    prev_inc_by_src = {}
    for i in income_prev:
        src = i['source']
        prev_inc_by_src[src] = prev_inc_by_src.get(src, 0) + i['amount']
    
    # Применяем фильтры к предыдущему периоду
    filtered_exp_prev, filtered_inc_prev, _ = apply_category_filters(
        user_id, prev_exp_by_cat, prev_inc_by_src
    )
    
    # Считаем суммы
    curr_total_exp = sum(filtered_exp_curr.values())
    prev_total_exp = sum(filtered_exp_prev.values())
    
    curr_total_inc = sum(filtered_inc_curr.values()) if filtered_inc_curr else 0
    prev_total_inc = sum(filtered_inc_prev.values()) if filtered_inc_prev else 0
    
    curr_balance = curr_total_inc - curr_total_exp
    prev_balance = prev_total_inc - prev_total_exp
    
    # Вычисляем изменения
    expenses_change = 0
    income_change = 0
    
    if prev_total_exp > 0:
        expenses_change = ((curr_total_exp - prev_total_exp) / prev_total_exp) * 100
    
    if prev_total_inc > 0:
        income_change = ((curr_total_inc - prev_total_inc) / prev_total_inc) * 100
    
    balance_change = curr_balance - prev_balance
    
    return {
        'current': {
            'total_expenses': curr_total_exp,
            'total_income': curr_total_inc,
            'balance': curr_balance
        },
        'previous': {
            'total_expenses': prev_total_exp,
            'total_income': prev_total_inc,
            'balance': prev_balance
        },
        'changes': {
            'expenses': expenses_change,
            'income': income_change,
            'balance': balance_change
        },
        'filters_applied': filters_applied
    }


def get_achievements(user_id: int) -> Dict:
    """Получить достижения пользователя"""
    stats_all = db.get_statistics(user_id, None)
    stats_30 = db.get_statistics(user_id, 30)
    
    achievements = []
    
    # Достижение за количество записей
    total_ops = stats_all['expenses_count'] + stats_all['income_count']
    if total_ops >= 100:
        achievements.append("🏆 Мастер учета - 100+ операций!")
    elif total_ops >= 50:
        achievements.append("🥈 Ученик - 50+ операций")
    elif total_ops >= 10:
        achievements.append("🥉 Новичок - 10+ операций")
    
    # Проверка Premium
    try:
        from subscription import subscription_manager
        if subscription_manager.is_premium(user_id):
            achievements.append("⭐ Premium пользователь")
    except:
        pass
    
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
    if stats_30['total_income'] > 0 and stats_30['balance'] > 0:
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
        'total_operations': total_ops
    }