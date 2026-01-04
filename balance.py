"""
Модуль управления виртуальным балансом
"""
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, Optional
from database import Database

db = Database()


class BalanceManager:
    """Управление виртуальным балансом пользователя"""
    
    def __init__(self):
        self._init_tables()
    
    def _init_tables(self):
        """Инициализация таблиц баланса"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_balance (
                    user_id BIGINT PRIMARY KEY,
                    balance REAL DEFAULT 0,
                    hidden_balance REAL DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hidden_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount REAL NOT NULL,
                    operation_type TEXT NOT NULL,
                    reason TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error initializing balance tables: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_balance(self, user_id: int) -> Dict:
        """Получить баланс пользователя"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM user_balance WHERE user_id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            
            if not row:
                self._create_balance(user_id)
                self.auto_initialize_balance(user_id)
                cursor.execute("""
                    SELECT * FROM user_balance WHERE user_id = %s
                """, (user_id,))
                row = cursor.fetchone()
            
            if not row:
                return {
                    'balance': 0,
                    'hidden_balance': 0,
                    'total_balance': 0
                }
            
            balance = dict(row)
            balance['total_balance'] = balance['balance'] + balance['hidden_balance']
            return balance
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def _create_balance(self, user_id: int):
        """Создать запись баланса"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_balance (user_id, balance, hidden_balance)
                VALUES (%s, 0, 0)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))
            conn.commit()
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def update_balance(self, user_id: int, amount: float, is_income: bool):
        """
        Обновить основной баланс
        
        Args:
            user_id: ID пользователя
            amount: Сумма
            is_income: True для дохода, False для расхода
        """
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            self._create_balance(user_id)
            
            if is_income:
                cursor.execute("""
                    UPDATE user_balance 
                    SET balance = balance + %s, last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (amount, user_id))
            else:
                cursor.execute("""
                    UPDATE user_balance 
                    SET balance = balance - %s, last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (amount, user_id))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error updating balance: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def add_to_hidden(self, user_id: int, amount: float, reason: str = None) -> bool:
        """
        Переместить деньги в скрытое
        
        Args:
            user_id: ID пользователя
            amount: Сумма для перемещения
            reason: Причина
        """
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            balance = self.get_balance(user_id)
            if balance['balance'] < amount:
                return False
            
            cursor.execute("""
                UPDATE user_balance 
                SET balance = balance - %s,
                    hidden_balance = hidden_balance + %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (amount, amount, user_id))
            
            cursor.execute("""
                INSERT INTO hidden_transactions 
                (user_id, amount, operation_type, reason)
                VALUES (%s, %s, 'add', %s)
            """, (user_id, amount, reason))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error adding to hidden: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def remove_from_hidden(self, user_id: int, amount: float, reason: str = None) -> bool:
        """
        Достать деньги из скрытого
        
        Args:
            user_id: ID пользователя
            amount: Сумма для возврата
            reason: Причина
        """
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            balance = self.get_balance(user_id)
            if balance['hidden_balance'] < amount:
                return False
            
            cursor.execute("""
                UPDATE user_balance 
                SET balance = balance + %s,
                    hidden_balance = hidden_balance - %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (amount, amount, user_id))
            
            cursor.execute("""
                INSERT INTO hidden_transactions 
                (user_id, amount, operation_type, reason)
                VALUES (%s, %s, 'remove', %s)
            """, (user_id, amount, reason))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error removing from hidden: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_hidden_history(self, user_id: int, limit: int = 20):
        """Получить историю операций со скрытыми деньгами"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM hidden_transactions
                WHERE user_id = %s
                ORDER BY date DESC
                LIMIT %s
            """, (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def recalculate_balance(self, user_id: int):
        """Пересчитать баланс с нуля на основе всех операций из БД"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_income
                FROM income WHERE user_id = %s
            """, (user_id,))
            total_income = cursor.fetchone()[0]
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_expenses
                FROM expenses WHERE user_id = %s
            """, (user_id,))
            total_expenses = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN operation_type = 'add' THEN amount ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN operation_type = 'remove' THEN amount ELSE 0 END), 0) as hidden
                FROM hidden_transactions WHERE user_id = %s
            """, (user_id,))
            result = cursor.fetchone()
            hidden_balance = result[0] if result else 0
            
            main_balance = total_income - total_expenses

            cursor.execute("""
                INSERT INTO user_balance (user_id, balance, hidden_balance)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    balance = EXCLUDED.balance,
                    hidden_balance = EXCLUDED.hidden_balance,
                    last_updated = CURRENT_TIMESTAMP
            """, (user_id, main_balance, hidden_balance))
            
            conn.commit()
            
            print(f"Balance recalculated for user {user_id}:")
            print(f"  Income: {total_income}")
            print(f"  Expenses: {total_expenses}")
            print(f"  Main balance: {main_balance}")
            print(f"  Hidden: {hidden_balance}")
            
        except Exception as e:
            conn.rollback()
            print(f"Error recalculating balance: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def auto_initialize_balance(self, user_id: int):
        """Автоматическая инициализация баланса при первом обращении"""
        balance = self.get_balance(user_id)
        if balance['balance'] == 0 and balance['hidden_balance'] == 0:
            conn = db.get_connection()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) FROM income WHERE user_id = %s
                """, (user_id,))
                income_count = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM expenses WHERE user_id = %s
                """, (user_id,))
                expenses_count = cursor.fetchone()[0]
                
                if income_count > 0 or expenses_count > 0:
                    print(f"Auto-initializing balance for user {user_id}")
                    self.recalculate_balance(user_id)
                    
            finally:
                cursor.close()
                db.return_connection(conn)


balance_manager = BalanceManager()