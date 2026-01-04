"""
Модуль управления подписками (Premium)
"""
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Optional, Dict
from database import Database

db = Database()


class SubscriptionManager:
    def __init__(self):
        pass
    
    def get_subscription(self, user_id: int) -> Dict:
        """Получить информацию о подписке пользователя"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('''
                SELECT * FROM subscriptions
                WHERE user_id = %s
            ''', (user_id,))
            
            row = cursor.fetchone()
            
            if not row:
                self._create_subscription(user_id)
                return {
                    'user_id': user_id,
                    'is_premium': False,
                    'premium_until': None,
                    'stars_paid': 0,
                    'days_left': 0
                }
            
            sub = dict(row)
            
            if sub['premium_until']:
                premium_until = sub['premium_until']
                if isinstance(premium_until, str):
                    premium_until = datetime.fromisoformat(premium_until)
                now = datetime.now()
                
                if premium_until > now:
                    sub['is_premium'] = True
                    sub['days_left'] = (premium_until - now).days
                else:
                    sub['is_premium'] = False
                    sub['days_left'] = 0
                    self._deactivate_premium(user_id)
            else:
                sub['is_premium'] = False
                sub['days_left'] = 0
            
            return sub
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def is_premium(self, user_id: int) -> bool:
        """Проверить, есть ли у пользователя Premium"""
        sub = self.get_subscription(user_id)
        return sub['is_premium']
    
    def _create_subscription(self, user_id: int):
        """Создать запись подписки"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO subscriptions (user_id, is_premium)
                VALUES (%s, 0)
                ON CONFLICT (user_id) DO NOTHING
            ''', (user_id,))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error creating subscription: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def activate_premium(self, user_id: int, months: int = 1) -> bool:
        """Активировать Premium подписку"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            sub = self.get_subscription(user_id)
            
            if sub['is_premium'] and sub['premium_until']:
                premium_until = sub['premium_until']
                if isinstance(premium_until, str):
                    premium_until = datetime.fromisoformat(premium_until)
                new_premium_until = premium_until + timedelta(days=30 * months)
            else:
                new_premium_until = datetime.now() + timedelta(days=30 * months)
            
            cursor.execute('''
                UPDATE subscriptions
                SET is_premium = 1,
                    premium_until = %s,
                    last_payment_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            ''', (new_premium_until, user_id))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error activating premium: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def _deactivate_premium(self, user_id: int):
        """Деактивировать Premium (внутренний метод)"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions
                SET is_premium = 0
                WHERE user_id = %s
            ''', (user_id,))
            
            conn.commit()
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def add_payment(self, user_id: int, stars_amount: int, 
                   payment_charge_id: str = None, 
                   telegram_payment_charge_id: str = None):
        """Добавить запись о платеже"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO payment_history 
                (user_id, stars_amount, payment_charge_id, telegram_payment_charge_id)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, stars_amount, payment_charge_id, telegram_payment_charge_id))
            
            cursor.execute('''
                UPDATE subscriptions
                SET stars_paid = stars_paid + %s
                WHERE user_id = %s
            ''', (stars_amount, user_id))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error adding payment: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_payment_history(self, user_id: int, limit: int = 10):
        """Получить историю платежей"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('''
                SELECT * FROM payment_history
                WHERE user_id = %s
                ORDER BY paid_at DESC
                LIMIT %s
            ''', (user_id, limit))
            
            payments = [dict(row) for row in cursor.fetchall()]
            return payments
        finally:
            cursor.close()
            db.return_connection(conn)


subscription_manager = SubscriptionManager()