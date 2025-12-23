from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional
from database import Database

class HiddenMoneyManager:
    def __init__(self):
        pass

    def add_hidden_money(self, user_id: int, amout:float, reason: str = "") -> bool:
        """Добавить скрытые деньги"""
        db = Database()
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO hidden_money (user_id, amount, reason)
                VALUES (%s, %s, %s)
            ''', (user_id, amout, reason))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error adding hidden money: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)

    def get_hidden_money(self, user_id: int) -> List[Dict]:
            """Получить все скрытые деньги пользователя"""
            db = Database()
            conn = db.get_connection()
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute('''
                    SELECT * FROM hidden_money
                    WHERE user_id = %s
                    ORDER BY id DESC
                ''', (user_id,))
                
                hidden_money = [dict(row) for row in cursor.fetchall()]
                
                return hidden_money
            finally:
                cursor.close()
                db.return_connection(conn)