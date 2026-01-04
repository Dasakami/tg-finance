"""
Система шаблонов для быстрого добавления частых операций
"""
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
from database import Database

db = Database()


class TemplatesManager:
    """Управление шаблонами операций"""
    
    def __init__(self):
        self._init_tables()
    
    def _init_tables(self):
        """Инициализация таблиц"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transaction_templates (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    template_name TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    icon TEXT,
                    use_count INTEGER DEFAULT 0,
                    is_favorite INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error initializing templates tables: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def create_template(self, user_id: int, template_name: str, transaction_type: str,
                       amount: float, category: str, description: str = None, 
                       icon: str = None) -> bool:
        """Создать шаблон"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO transaction_templates 
                (user_id, template_name, transaction_type, amount, category, description, icon)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, template_name, transaction_type, amount, category, description, icon))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error creating template: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_templates(self, user_id: int, transaction_type: str = None) -> List[Dict]:
        """Получить шаблоны"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if transaction_type:
                cursor.execute("""
                    SELECT * FROM transaction_templates
                    WHERE user_id = %s AND transaction_type = %s
                    ORDER BY is_favorite DESC, use_count DESC, template_name
                """, (user_id, transaction_type))
            else:
                cursor.execute("""
                    SELECT * FROM transaction_templates
                    WHERE user_id = %s
                    ORDER BY is_favorite DESC, use_count DESC, template_name
                """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def use_template(self, template_id: int, user_id: int) -> Optional[Dict]:
        """Использовать шаблон (возвращает данные для создания операции)"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM transaction_templates
                WHERE id = %s AND user_id = %s
            """, (template_id, user_id))
            
            template = cursor.fetchone()
            if not template:
                return None
            cursor.execute("""
                UPDATE transaction_templates
                SET use_count = use_count + 1,
                    last_used = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (template_id,))
            
            conn.commit()
            
            return dict(template)
        except Exception as e:
            conn.rollback()
            print(f"Error using template: {e}")
            return None
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def toggle_favorite(self, template_id: int, user_id: int) -> bool:
        """Переключить избранное"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE transaction_templates
                SET is_favorite = 1 - is_favorite
                WHERE id = %s AND user_id = %s
            """, (template_id, user_id))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error toggling favorite: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def delete_template(self, template_id: int, user_id: int) -> bool:
        """Удалить шаблон"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM transaction_templates
                WHERE id = %s AND user_id = %s
            """, (template_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting template: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_popular_templates(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Получить самые используемые шаблоны"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM transaction_templates
                WHERE user_id = %s
                ORDER BY use_count DESC
                LIMIT %s
            """, (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def auto_suggest_templates(self, user_id: int) -> List[Dict]:
        """Авто-предложение шаблонов на основе частых операций"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT 
                    category,
                    amount,
                    description,
                    COUNT(*) as frequency
                FROM expenses
                WHERE user_id = %s
                GROUP BY category, amount, description
                HAVING COUNT(*) >= 3
                ORDER BY frequency DESC
                LIMIT 5
            """, (user_id,))
            
            suggestions = []
            for row in cursor.fetchall():
                cursor.execute("""
                    SELECT COUNT(*) FROM transaction_templates
                    WHERE user_id = %s 
                    AND category = %s 
                    AND amount = %s
                """, (user_id, row['category'], row['amount']))
                
                exists = cursor.fetchone()[0] > 0
                
                if not exists:
                    suggestions.append({
                        'category': row['category'],
                        'amount': row['amount'],
                        'description': row['description'],
                        'frequency': row['frequency'],
                        'suggested_name': f"{row['category']} {row['amount']} сом"
                    })
            
            return suggestions
        finally:
            cursor.close()
            db.return_connection(conn)


templates_manager = TemplatesManager()