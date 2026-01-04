"""
Система тегов для операций - быстрая фильтрация и группировка
"""
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
from database import Database

db = Database()


class TagsManager:
    """Управление тегами для операций"""
    
    def __init__(self):
        self._init_tables()
    
    def _init_tables(self):
        """Инициализация таблиц"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    tag_name TEXT NOT NULL,
                    color TEXT DEFAULT '#3498db',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, tag_name),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expense_tags (
                    expense_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (expense_id, tag_id),
                    FOREIGN KEY (expense_id) REFERENCES expenses (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS income_tags (
                    income_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (income_id, tag_id),
                    FOREIGN KEY (income_id) REFERENCES income (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error initializing tags tables: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def create_tag(self, user_id: int, tag_name: str, color: str = '#3498db') -> Optional[int]:
        """Создать новый тег"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tags (user_id, tag_name, color)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, tag_name) DO NOTHING
                RETURNING id
            """, (user_id, tag_name, color))
            
            result = cursor.fetchone()
            conn.commit()
            
            return result[0] if result else None
        except Exception as e:
            conn.rollback()
            print(f"Error creating tag: {e}")
            return None
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_or_create_tag(self, user_id: int, tag_name: str) -> Optional[int]:
        """Получить ID тега или создать если не существует"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM tags WHERE user_id = %s AND tag_name = %s
            """, (user_id, tag_name))
            
            row = cursor.fetchone()
            if row:
                return row[0]
            
            return self.create_tag(user_id, tag_name)
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def add_tag_to_expense(self, expense_id: int, tag_id: int) -> bool:
        """Добавить тег к расходу"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO expense_tags (expense_id, tag_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (expense_id, tag_id))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error adding tag to expense: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_user_tags(self, user_id: int) -> List[Dict]:
        """Получить все теги пользователя"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    t.*,
                    (SELECT COUNT(*) FROM expense_tags et WHERE et.tag_id = t.id) as expense_count,
                    (SELECT COUNT(*) FROM income_tags it WHERE it.tag_id = t.id) as income_count
                FROM tags t
                WHERE t.user_id = %s
                ORDER BY t.tag_name
            """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_expense_tags(self, expense_id: int) -> List[Dict]:
        """Получить теги расхода"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT t.* FROM tags t
                JOIN expense_tags et ON et.tag_id = t.id
                WHERE et.expense_id = %s
            """, (expense_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_expenses_by_tag(self, user_id: int, tag_name: str, days: int = None) -> List[Dict]:
        """Получить все расходы с определённым тегом"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if days:
                from datetime import datetime, timedelta
                date_from = datetime.now() - timedelta(days=days)
                
                cursor.execute("""
                    SELECT e.* FROM expenses e
                    JOIN expense_tags et ON et.expense_id = e.id
                    JOIN tags t ON t.id = et.tag_id
                    WHERE e.user_id = %s AND t.tag_name = %s AND e.date >= %s
                    ORDER BY e.date DESC
                """, (user_id, tag_name, date_from))
            else:
                cursor.execute("""
                    SELECT e.* FROM expenses e
                    JOIN expense_tags et ON et.expense_id = e.id
                    JOIN tags t ON t.id = et.tag_id
                    WHERE e.user_id = %s AND t.tag_name = %s
                    ORDER BY e.date DESC
                """, (user_id, tag_name))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_popular_tags(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получить самые используемые теги"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    t.*,
                    (SELECT COUNT(*) FROM expense_tags et WHERE et.tag_id = t.id) +
                    (SELECT COUNT(*) FROM income_tags it WHERE it.tag_id = t.id) as usage_count
                FROM tags t
                WHERE t.user_id = %s
                ORDER BY usage_count DESC
                LIMIT %s
            """, (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def delete_tag(self, user_id: int, tag_id: int) -> bool:
        """Удалить тег"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM tags
                WHERE id = %s AND user_id = %s
            """, (tag_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting tag: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)


tags_manager = TagsManager()