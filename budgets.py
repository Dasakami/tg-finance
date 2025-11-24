import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from database import Database

db = Database()


class BudgetManager:
    def __init__(self):
        self.init_budgets_table()
    
    def init_budgets_table(self):
        """Инициализация таблицы бюджетов"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                limit_amount REAL NOT NULL,
                period TEXT DEFAULT 'monthly',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category, period),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def set_budget(self, user_id: int, category: str, amount: float, period: str = 'monthly') -> bool:
        """Установить бюджет для категории"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO budgets (user_id, category, limit_amount, period)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, category, period) 
                DO UPDATE SET limit_amount = ?, created_at = CURRENT_TIMESTAMP
            ''', (user_id, category, amount, period, amount))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error setting budget: {e}")
            return False
        finally:
            conn.close()
    
    def get_budgets(self, user_id: int) -> List[Dict]:
        """Получить все бюджеты пользователя"""
        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM budgets
            WHERE user_id = ?
            ORDER BY category
        ''', (user_id,))
        
        budgets = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Добавляем информацию о текущих тратах
        stats = db.get_statistics(user_id, 30)
        for budget in budgets:
            spent = stats['expenses_by_category'].get(budget['category'], 0)
            budget['spent'] = spent
            budget['remaining'] = budget['limit_amount'] - spent
            budget['percent_used'] = (spent / budget['limit_amount'] * 100) if budget['limit_amount'] > 0 else 0
        
        return budgets
    
    def delete_budget(self, user_id: int, category: str) -> bool:
        """Удалить бюджет"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM budgets
            WHERE user_id = ? AND category = ?
        ''', (user_id, category))
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def check_budget_alerts(self, user_id: int, category: str) -> Optional[Dict]:
        """Проверить, не превышен ли бюджет"""
        budgets = self.get_budgets(user_id)
        
        for budget in budgets:
            if budget['category'].lower() == category.lower():
                if budget['percent_used'] >= 100:
                    return {
                        'type': 'exceeded',
                        'category': category,
                        'limit': budget['limit_amount'],
                        'spent': budget['spent'],
                        'over': budget['spent'] - budget['limit_amount']
                    }
                elif budget['percent_used'] >= 80:
                    return {
                        'type': 'warning',
                        'category': category,
                        'limit': budget['limit_amount'],
                        'spent': budget['spent'],
                        'remaining': budget['remaining'],
                        'percent': budget['percent_used']
                    }
        
        return None
    
    def get_budget_summary(self, user_id: int) -> Dict:
        """Получить сводку по всем бюджетам"""
        budgets = self.get_budgets(user_id)
        
        total_budget = sum(b['limit_amount'] for b in budgets)
        total_spent = sum(b['spent'] for b in budgets)
        
        exceeded = [b for b in budgets if b['percent_used'] >= 100]
        warning = [b for b in budgets if 80 <= b['percent_used'] < 100]
        safe = [b for b in budgets if b['percent_used'] < 80]
        
        return {
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_remaining': total_budget - total_spent,
            'budgets_count': len(budgets),
            'exceeded': exceeded,
            'warning': warning,
            'safe': safe
        }


budget_manager = BudgetManager()