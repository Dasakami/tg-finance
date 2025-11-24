import sqlite3
from typing import List, Dict
from database import Database

db = Database()


class CategoryFilter:
    def __init__(self):
        self.init_filter_table()
    
    def init_filter_table(self):
        """Инициализация таблицы фильтров"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS category_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                is_excluded INTEGER DEFAULT 0,
                filter_type TEXT DEFAULT 'expense',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category, filter_type),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_filter(self, user_id: int, category: str, is_excluded: bool = True, 
                   filter_type: str = 'expense') -> bool:
        """Добавить фильтр категории"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO category_filters (user_id, category, is_excluded, filter_type)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, category, filter_type) 
                DO UPDATE SET is_excluded = ?
            ''', (user_id, category, 1 if is_excluded else 0, filter_type, 1 if is_excluded else 0))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding filter: {e}")
            return False
        finally:
            conn.close()
    
    def remove_filter(self, user_id: int, category: str, filter_type: str = 'expense') -> bool:
        """Удалить фильтр категории"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM category_filters
            WHERE user_id = ? AND category = ? AND filter_type = ?
        ''', (user_id, category, filter_type))
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def get_excluded_categories(self, user_id: int, filter_type: str = 'expense') -> List[str]:
        """Получить список исключенных категорий"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT category FROM category_filters
            WHERE user_id = ? AND filter_type = ? AND is_excluded = 1
        ''', (user_id, filter_type))
        
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        return categories
    
    def get_included_categories(self, user_id: int, filter_type: str = 'expense') -> List[str]:
        """Получить список включенных категорий (только они учитываются)"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT category FROM category_filters
            WHERE user_id = ? AND filter_type = ? AND is_excluded = 0
        ''', (user_id, filter_type))
        
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        return categories
    
    def get_all_filters(self, user_id: int) -> Dict:
        """Получить все фильтры пользователя"""
        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM category_filters
            WHERE user_id = ?
            ORDER BY filter_type, category
        ''', (user_id,))
        
        filters = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        result = {
            'expense_excluded': [],
            'expense_included': [],
            'income_excluded': [],
            'income_included': []
        }
        
        for f in filters:
            key = f"{f['filter_type']}_{'excluded' if f['is_excluded'] else 'included'}"
            if key in result:
                result[key].append(f['category'])
        
        return result
    
    def clear_all_filters(self, user_id: int) -> bool:
        """Очистить все фильтры пользователя"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM category_filters
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def apply_filters(self, user_id: int, data: Dict, filter_type: str = 'expense') -> Dict:
        """
        Применить фильтры к данным статистики
        
        Args:
            user_id: ID пользователя
            data: Словарь с категориями и суммами
            filter_type: 'expense' или 'income'
        
        Returns:
            Отфильтрованный словарь
        """
        excluded = self.get_excluded_categories(user_id, filter_type)
        included = self.get_included_categories(user_id, filter_type)
        
        if included:
            return {k: v for k, v in data.items() if k in included}
        
        if excluded:
            return {k: v for k, v in data.items() if k not in excluded}
        
        return data


category_filter = CategoryFilter()