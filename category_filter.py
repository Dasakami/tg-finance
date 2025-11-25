from psycopg2.extras import RealDictCursor
from typing import List, Dict
from database import Database

db = Database()


class CategoryFilter:
    def __init__(self):
        # Таблица уже создается в database.py
        pass
    
    def add_filter(self, user_id: int, category: str, is_excluded: bool = True, 
                   filter_type: str = 'expense') -> bool:
        """Добавить фильтр категории"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO category_filters (user_id, category, is_excluded, filter_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, category, filter_type) 
                DO UPDATE SET is_excluded = %s
            ''', (user_id, category, 1 if is_excluded else 0, filter_type, 1 if is_excluded else 0))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error adding filter: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def remove_filter(self, user_id: int, category: str, filter_type: str = 'expense') -> bool:
        """Удалить фильтр категории"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM category_filters
                WHERE user_id = %s AND category = %s AND filter_type = %s
            ''', (user_id, category, filter_type))
            
            conn.commit()
            deleted = cursor.rowcount > 0
            return deleted
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_excluded_categories(self, user_id: int, filter_type: str = 'expense') -> List[str]:
        """Получить список исключенных категорий"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT category FROM category_filters
                WHERE user_id = %s AND filter_type = %s AND is_excluded = 1
            ''', (user_id, filter_type))
            
            categories = [row[0] for row in cursor.fetchall()]
            return categories
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_included_categories(self, user_id: int, filter_type: str = 'expense') -> List[str]:
        """Получить список включенных категорий (только они учитываются)"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT category FROM category_filters
                WHERE user_id = %s AND filter_type = %s AND is_excluded = 0
            ''', (user_id, filter_type))
            
            categories = [row[0] for row in cursor.fetchall()]
            return categories
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_all_filters(self, user_id: int) -> Dict:
        """Получить все фильтры пользователя"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('''
                SELECT * FROM category_filters
                WHERE user_id = %s
                ORDER BY filter_type, category
            ''', (user_id,))
            
            filters = [dict(row) for row in cursor.fetchall()]
            
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
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def clear_all_filters(self, user_id: int) -> bool:
        """Очистить все фильтры пользователя"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM category_filters
                WHERE user_id = %s
            ''', (user_id,))
            
            conn.commit()
            deleted = cursor.rowcount > 0
            return deleted
        finally:
            cursor.close()
            db.return_connection(conn)
    
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