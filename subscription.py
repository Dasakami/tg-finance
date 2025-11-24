"""
Модуль управления подписками (Premium)
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict
from database import Database

db = Database()


class SubscriptionManager:
    def __init__(self):
        self.init_subscription_table()
    
    def init_subscription_table(self):
        """Инициализация таблицы подписок"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                is_premium INTEGER DEFAULT 0,
                premium_until TIMESTAMP,
                stars_paid INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_payment_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица истории платежей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stars_amount INTEGER NOT NULL,
                payment_charge_id TEXT,
                telegram_payment_charge_id TEXT,
                paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_subscription(self, user_id: int) -> Dict:
        """Получить информацию о подписке пользователя"""
        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM subscriptions
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            # Создаем запись для нового пользователя
            self._create_subscription(user_id)
            return {
                'user_id': user_id,
                'is_premium': False,
                'premium_until': None,
                'stars_paid': 0,
                'days_left': 0
            }
        
        sub = dict(row)
        
        # Проверяем, не истекла ли подписка
        if sub['premium_until']:
            premium_until = datetime.fromisoformat(sub['premium_until'])
            now = datetime.now()
            
            if premium_until > now:
                sub['is_premium'] = True
                sub['days_left'] = (premium_until - now).days
            else:
                # Подписка истекла
                sub['is_premium'] = False
                sub['days_left'] = 0
                self._deactivate_premium(user_id)
        else:
            sub['is_premium'] = False
            sub['days_left'] = 0
        
        return sub
    
    def is_premium(self, user_id: int) -> bool:
        """Проверить, есть ли у пользователя Premium"""
        sub = self.get_subscription(user_id)
        return sub['is_premium']
    
    def _create_subscription(self, user_id: int):
        """Создать запись подписки"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO subscriptions (user_id, is_premium)
            VALUES (?, 0)
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def activate_premium(self, user_id: int, months: int = 1) -> bool:
        """Активировать Premium подписку"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Получаем текущую подписку
        sub = self.get_subscription(user_id)
        
        # Если подписка активна, продлеваем от текущей даты окончания
        if sub['is_premium'] and sub['premium_until']:
            premium_until = datetime.fromisoformat(sub['premium_until'])
            new_premium_until = premium_until + timedelta(days=30 * months)
        else:
            # Если подписки нет, активируем с текущего момента
            new_premium_until = datetime.now() + timedelta(days=30 * months)
        
        try:
            cursor.execute('''
                UPDATE subscriptions
                SET is_premium = 1,
                    premium_until = ?,
                    last_payment_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (new_premium_until.isoformat(), user_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error activating premium: {e}")
            return False
        finally:
            conn.close()
    
    def _deactivate_premium(self, user_id: int):
        """Деактивировать Premium (внутренний метод)"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE subscriptions
            SET is_premium = 0
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def add_payment(self, user_id: int, stars_amount: int, 
                   payment_charge_id: str = None, 
                   telegram_payment_charge_id: str = None):
        """Добавить запись о платеже"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payment_history 
            (user_id, stars_amount, payment_charge_id, telegram_payment_charge_id)
            VALUES (?, ?, ?, ?)
        ''', (user_id, stars_amount, payment_charge_id, telegram_payment_charge_id))
        
        # Обновляем счетчик звезд
        cursor.execute('''
            UPDATE subscriptions
            SET stars_paid = stars_paid + ?
            WHERE user_id = ?
        ''', (stars_amount, user_id))
        
        conn.commit()
        conn.close()
    
    def get_payment_history(self, user_id: int, limit: int = 10):
        """Получить историю платежей"""
        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM payment_history
            WHERE user_id = ?
            ORDER BY paid_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        payments = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return payments


subscription_manager = SubscriptionManager()