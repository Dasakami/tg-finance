import os
import uuid
from typing import Dict, Optional, List

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def _prepare_chart_data(data: Dict[str, float], excluded_categories: List[str] = None):
    """Подготовка данных с учетом исключенных категорий"""
    if not data:
        return ["Нет данных"], [1], []
    
    if excluded_categories:
        data = {k: v for k, v in data.items() if k not in excluded_categories}
    
    if not data:
        return ["Нет данных"], [1], []
    
    labels = []
    values = []
    colors_list = []
    
    colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
        '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',
        '#FF8FAB', '#06D6A0', '#118AB2', '#EF476F', '#FFD166'
    ]
    
    for idx, (label, value) in enumerate(sorted(data.items(), key=lambda x: x[1], reverse=True)):
        labels.append(label)
        values.append(value)
        colors_list.append(colors[idx % len(colors)])
    
    return labels, values, colors_list


def create_pie_chart(data: Dict[str, float], title: str, excluded_categories: List[str] = None) -> Optional[str]:
    """Круговая диаграмма с легендой в углу"""
    labels, values, colors = _prepare_chart_data(data, excluded_categories)
    
    if not values or (len(values) == 1 and labels[0] == "Нет данных"):
        return None
    
    fig, ax = plt.subplots(figsize=(10, 7))
    plt.rcParams['font.family'] = 'DejaVu Sans'
    
    # Создаем круговую диаграмму БЕЗ подписей
    wedges, texts, autotexts = ax.pie(
        values, 
        autopct='%1.1f%%',
        startangle=140,
        colors=colors,
        textprops={'fontsize': 10, 'weight': 'bold'}
    )
    
    # Создаем легенду в углу
    legend_labels = [f'{label}: {value:,.0f} руб.' for label, value in zip(labels, values)]
    ax.legend(
        wedges, 
        legend_labels,
        title="Категории",
        loc="upper left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=9
    )
    
    ax.set_title(title, fontsize=14, weight='bold', pad=20)
    
    plt.tight_layout()
    filename = f"pie_chart_{uuid.uuid4().hex}.png"
    filepath = os.path.join(os.getcwd(), filename)
    fig.savefig(filepath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return filepath


def create_bar_chart(data: Dict[str, float], title: str, excluded_categories: List[str] = None) -> Optional[str]:
    """Столбчатая диаграмма с легендой"""
    labels, values, colors = _prepare_chart_data(data, excluded_categories)
    
    if not values or (len(values) == 1 and labels[0] == "Нет данных"):
        return None
    
    fig, ax = plt.subplots(figsize=(12, 7))
    plt.rcParams['font.family'] = 'DejaVu Sans'
    
    # Создаем столбчатую диаграмму
    bars = ax.bar(range(len(labels)), values, color=colors, edgecolor='black', linewidth=0.5)
    
    # Настройка осей
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(range(1, len(labels) + 1))  # Нумеруем столбцы
    ax.set_ylabel('Сумма (руб.)', fontsize=11, weight='bold')
    ax.set_title(title, fontsize=14, weight='bold', pad=20)
    
    # Добавляем значения на столбцы
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2., height,
            f'{value:,.0f}',
            ha='center', va='bottom', fontsize=9, weight='bold'
        )
    
    # Создаем легенду
    legend_patches = [mpatches.Patch(color=color, label=f'{i+1}. {label}') 
                     for i, (label, color) in enumerate(zip(labels, colors))]
    ax.legend(
        handles=legend_patches,
        title="Категории",
        loc="upper right",
        fontsize=9
    )
    
    # Сетка
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    filename = f"bar_chart_{uuid.uuid4().hex}.png"
    filepath = os.path.join(os.getcwd(), filename)
    fig.savefig(filepath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return filepath


def create_line_chart(expenses_data: Dict[str, float], income_data: Dict[str, float], 
                     title: str, excluded_categories: List[str] = None) -> Optional[str]:
    """Линейная диаграмма для сравнения расходов и доходов"""
    
    # Подготовка данных
    exp_labels, exp_values, exp_colors = _prepare_chart_data(expenses_data, excluded_categories)
    inc_labels, inc_values, inc_colors = _prepare_chart_data(income_data)
    
    if (not exp_values or (len(exp_values) == 1 and exp_labels[0] == "Нет данных")) and \
       (not inc_values or (len(inc_values) == 1 and inc_labels[0] == "Нет данных")):
        return None
    
    fig, ax = plt.subplots(figsize=(12, 7))
    plt.rcParams['font.family'] = 'DejaVu Sans'
    
    x_exp = range(len(exp_labels))
    x_inc = range(len(inc_labels))
    
    # Линии
    if exp_values and exp_labels[0] != "Нет данных":
        ax.plot(x_exp, exp_values, marker='o', linewidth=2, markersize=8, 
               color='#FF6B6B', label='Расходы', linestyle='-')
        
        # Подписи значений
        for i, (x, y) in enumerate(zip(x_exp, exp_values)):
            ax.text(x, y, f'{y:,.0f}', fontsize=8, ha='center', va='bottom')
    
    if inc_values and inc_labels[0] != "Нет данных":
        ax.plot(x_inc, inc_values, marker='s', linewidth=2, markersize=8,
               color='#4ECDC4', label='Доходы', linestyle='-')
        
        # Подписи значений
        for i, (x, y) in enumerate(zip(x_inc, inc_values)):
            ax.text(x, y, f'{y:,.0f}', fontsize=8, ha='center', va='top')
    
    # Настройка осей
    all_labels = exp_labels if len(exp_labels) >= len(inc_labels) else inc_labels
    ax.set_xticks(range(len(all_labels)))
    ax.set_xticklabels([f'{i+1}' for i in range(len(all_labels))], fontsize=9)
    ax.set_ylabel('Сумма (руб.)', fontsize=11, weight='bold')
    ax.set_title(title, fontsize=14, weight='bold', pad=20)
    
    # Легенда категорий
    legend_text = "Категории (расходы):\n"
    for i, label in enumerate(exp_labels[:10], 1):
        legend_text += f"{i}. {label}\n"
    
    if inc_labels and inc_labels[0] != "Нет данных":
        legend_text += "\nИсточники (доходы):\n"
        for i, label in enumerate(inc_labels[:10], 1):
            legend_text += f"{i}. {label}\n"
    
    ax.text(
        1.02, 0.5, legend_text,
        transform=ax.transAxes,
        fontsize=8,
        verticalalignment='center',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3)
    )
    
    ax.legend(loc='upper left', fontsize=10)

    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    filename = f"line_chart_{uuid.uuid4().hex}.png"
    filepath = os.path.join(os.getcwd(), filename)
    fig.savefig(filepath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return filepath


def create_statistics_chart(stats: Dict, period_text: str = "30 дней", 
                           chart_type: str = "pie",
                           excluded_categories: List[str] = None) -> Optional[str]:
    """
    Создает диаграмму статистики за указанный период
    
    Args:
        stats: Словарь со статистикой
        period_text: Текстовое описание периода
        chart_type: Тип диаграммы ("pie", "bar", "line")
        excluded_categories: Список исключенных категорий
    """
    expenses = stats.get('expenses_by_category', {})
    income = stats.get('income_by_source', {})
    
    if not expenses and not income:
        return None
    
    title_suffix = f" ({period_text})"
    if excluded_categories:
        title_suffix += f" [исключено: {len(excluded_categories)}]"
    
    if chart_type == "pie":
        charts_count = 2 if expenses and income else 1
        figsize = (18, 7) if charts_count == 2 else (10, 7)
        fig, axes = plt.subplots(1, charts_count, figsize=figsize)
        plt.rcParams['font.family'] = 'DejaVu Sans'
        
        if charts_count == 1:
            axes = [axes]
        else:
            axes = list(axes)
        
        if expenses:
            labels, values, colors = _prepare_chart_data(expenses, excluded_categories)
            ax = axes[0]
            wedges, texts, autotexts = ax.pie(
                values, autopct='%1.1f%%', startangle=140, colors=colors,
                textprops={'fontsize': 9, 'weight': 'bold'}
            )
            legend_labels = [f'{l}: {v:,.0f} руб.' for l, v in zip(labels, values)]
            ax.legend(wedges, legend_labels, title="Категории", 
                     loc="upper left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=8)
            ax.set_title(f'Расходы по категориям{title_suffix}', fontsize=12, weight='bold')

        if charts_count == 2 and income:
            labels, values, colors = _prepare_chart_data(income)
            ax = axes[1]
            wedges, texts, autotexts = ax.pie(
                values, autopct='%1.1f%%', startangle=140, colors=colors,
                textprops={'fontsize': 9, 'weight': 'bold'}
            )
            legend_labels = [f'{l}: {v:,.0f} руб.' for l, v in zip(labels, values)]
            ax.legend(wedges, legend_labels, title="Источники",
                     loc="upper left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=8)
            ax.set_title(f'Доходы по источникам{title_suffix}', fontsize=12, weight='bold')
        
        plt.tight_layout()
        filename = f"stats_pie_{uuid.uuid4().hex}.png"
        
    elif chart_type == "bar":
        return create_bar_chart(expenses, f'Расходы по категориям{title_suffix}', excluded_categories)
        
    elif chart_type == "line":
        return create_line_chart(expenses, income, f'Сравнение расходов и доходов{title_suffix}', excluded_categories)
    
    else:
        return None
    
    filepath = os.path.join(os.getcwd(), filename)
    fig.savefig(filepath, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return filepath