"""
Модуль управления пользовательскими категориями
"""
from psycopg2.extras import RealDictCursor
from typing import List, Dict
from database import Database

db = Database()


class CustomCategoryManager:
    """Управление пользовательскими категориями"""
    DEFAULT_EXPENSE_CATEGORIES = [
        "🍔 Еда", "🚗 Транспорт", "🛒 Покупки", "💊 Здоровье",
        "🏠 Жилье", "🎮 Развлечения", "👕 Одежда", "📚 Образование"
    ]
    DEFAULT_INCOME_SOURCES = [
        "💼 Зарплата", "💻 Фриланс", "📈 Инвестиции", 
        "🏪 Бизнес", "🎁 Подарки", "💰 Прочее"
    ]
    
    def __init__(self):
        self._init_tables()
    
    def _init_tables(self):
        """Инициализация таблиц"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_categories (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    category_name TEXT NOT NULL,
                    category_type TEXT NOT NULL,
                    icon TEXT,
                    is_favorite INTEGER DEFAULT 0,
                    use_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, category_name, category_type),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_custom_categories_user 
                ON custom_categories (user_id, category_type)
            """)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error initializing custom categories: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def add_category(self, user_id: int, category_name: str, 
                    category_type: str = 'expense', icon: str = None) -> bool:
        """
        Добавить пользовательскую категорию
        
        Args:
            user_id: ID пользователя
            category_name: Название категории
            category_type: 'expense' или 'income'
            icon: Эмодзи для категории
        """
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO custom_categories 
                (user_id, category_name, category_type, icon)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, category_name, category_type) DO NOTHING
            """, (user_id, category_name, category_type, icon))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error adding custom category: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_categories(self, user_id: int, category_type: str = 'expense') -> List[Dict]:
        """
        Получить все категории пользователя (стандартные + пользовательские)
        
        Args:
            user_id: ID пользователя
            category_type: 'expense' или 'income'
        """
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM custom_categories
                WHERE user_id = %s AND category_type = %s
                ORDER BY is_favorite DESC, use_count DESC, category_name
            """, (user_id, category_type))
            
            custom = [dict(row) for row in cursor.fetchall()]

            if category_type == 'expense':
                defaults = self.DEFAULT_EXPENSE_CATEGORIES
            else:
                defaults = self.DEFAULT_INCOME_SOURCES
            
            result = []
            for cat in custom:
                name = cat['category_name']
                if cat['icon']:
                    name = f"{cat['icon']} {name}"
                result.append({
                    'name': name,
                    'is_custom': True,
                    'is_favorite': cat['is_favorite']
                })
            
            for def_cat in defaults:
                result.append({
                    'name': def_cat,
                    'is_custom': False,
                    'is_favorite': False
                })
            
            return result
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def delete_category(self, user_id: int, category_name: str, 
                       category_type: str = 'expense') -> bool:
        """Удалить пользовательскую категорию"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM custom_categories
                WHERE user_id = %s AND category_name = %s AND category_type = %s
            """, (user_id, category_name, category_type))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting category: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def toggle_favorite(self, user_id: int, category_name: str, 
                       category_type: str = 'expense'):
        """Переключить избранное для категории"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE custom_categories
                SET is_favorite = 1 - is_favorite
                WHERE user_id = %s AND category_name = %s AND category_type = %s
            """, (user_id, category_name, category_type))
            
            conn.commit()
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def increment_use_count(self, user_id: int, category_name: str, 
                           category_type: str = 'expense'):
        """Увеличить счётчик использования категории"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            clean_name = category_name.split(' ', 1)[-1] if ' ' in category_name else category_name
            
            cursor.execute("""
                UPDATE custom_categories
                SET use_count = use_count + 1
                WHERE user_id = %s AND category_name = %s AND category_type = %s
            """, (user_id, clean_name, category_type))
            
            conn.commit()
        except Exception as e:
            print(f"Error incrementing use count: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_popular_categories(self, user_id: int, category_type: str = 'expense', 
                              limit: int = 5) -> List[str]:
        """Получить самые используемые категории"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT category_name, icon FROM custom_categories
                WHERE user_id = %s AND category_type = %s
                ORDER BY use_count DESC
                LIMIT %s
            """, (user_id, category_type, limit))
            
            result = []
            for row in cursor.fetchall():
                name = row[0]
                icon = row[1]
                if icon:
                    name = f"{icon} {name}"
                result.append(name)
            
            return result
        finally:
            cursor.close()
            db.return_connection(conn)


category_manager = CustomCategoryManager()