import os
import uuid
from typing import Dict, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def _prepare_chart_data(data: Dict[str, float]):
    """Подготовка данных для диаграммы"""
    if not data:
        return ["Нет данных"], [1]
    
    labels = []
    values = []
    
    for label, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
        labels.append(label)
        values.append(value)
    
    return labels, values


def create_statistics_chart(stats: Dict, period_text: str = "30 дней") -> Optional[str]:
    """
    Создает диаграмму статистики за указанный период
    
    Args:
        stats: Словарь со статистикой
        period_text: Текстовое описание периода (например, "30 дней" или "все время")
    
    Returns:
        Путь к файлу с диаграммой или None
    """
    expenses = stats.get('expenses_by_category', {})
    income = stats.get('income_by_source', {})
    
    if not expenses and not income:
        return None
    
    charts_count = 2 if expenses and income else 1
    figsize = (12, 6) if charts_count == 2 else (6, 6)
    fig, axes = plt.subplots(1, charts_count, figsize=figsize)
    
    if charts_count == 1:
        axes = [axes]
    else:
        axes = list(axes)
    plt.rcParams['font.family'] = 'DejaVu Sans'
    
    if expenses:
        labels, values = _prepare_chart_data(expenses)
        ax = axes[0]
        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, textprops={'fontsize': 9})
        ax.set_title(f'Расходы по категориям ({period_text})', fontsize=12)
    else:
        ax = axes[0]
        ax.axis('off')
        ax.text(0.5, 0.5, 'Недостаточно данных по расходам', ha='center', va='center', fontsize=12)
    
    if charts_count == 2:
        labels, values = _prepare_chart_data(income)
        ax = axes[1]
        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, textprops={'fontsize': 9})
        ax.set_title(f'Доходы по источникам ({period_text})', fontsize=12)
    elif income and not expenses:
        ax = axes[0]
        ax.clear()
        labels, values = _prepare_chart_data(income)
        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, textprops={'fontsize': 9})
        ax.set_title(f'Доходы по источникам ({period_text})', fontsize=12)
    
    plt.tight_layout()
    
    filename = f"stats_chart_{uuid.uuid4().hex}.png"
    filepath = os.path.join(os.getcwd(), filename)
    
    try:
        fig.savefig(filepath, dpi=200, bbox_inches='tight')
        plt.close(fig)
        return filepath
    except Exception as e:
        print(f"Error saving chart: {e}")
        plt.close(fig)
        return None