import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import os
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.connection_pool = None
        self._init_connection_pool()
        self.init_database()

    def _init_connection_pool(self):
        """Инициализация пула соединений"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                dbname=os.getenv("DB_NAME", "finance_bot"),
                user=os.getenv("DB_USER", "finance_user"),
                password=os.getenv("DB_PASSWORD", "h72ivh-19"),
                host=os.getenv("DB_HOST", "finance_bot_db"),
                port=os.getenv("DB_PORT", "5432")
            )
            logger.info("Connection pool created successfully")
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise

    def get_connection(self):
        """Получить соединение из пула"""
        try:
            return self.connection_pool.getconn()
        except Exception as e:
            logger.error(f"Error getting connection: {e}")
            raise

    def return_connection(self, conn):
        """Вернуть соединение в пул"""
        if conn:
            self.connection_pool.putconn(conn)

    def init_database(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица расходов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица доходов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS income (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount REAL NOT NULL,
                    source TEXT NOT NULL,
                    description TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Индексы
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_expenses_user_date 
                ON expenses (user_id, date DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_income_user_date 
                ON income (user_id, date DESC)
            """)

            # Таблица бюджетов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    category TEXT NOT NULL,
                    limit_amount REAL NOT NULL,
                    period TEXT DEFAULT 'monthly',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, category, period),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица фильтров категорий
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS category_filters (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    category TEXT NOT NULL,
                    is_excluded INTEGER DEFAULT 0,
                    filter_type TEXT DEFAULT 'expense',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, category, filter_type),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица подписок
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    is_premium INTEGER DEFAULT 0,
                    premium_until TIMESTAMP,
                    stars_paid INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_payment_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица истории платежей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    stars_amount INTEGER NOT NULL,
                    payment_charge_id TEXT,
                    telegram_payment_charge_id TEXT,
                    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Групповые расходы
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_expenses (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    user_name TEXT,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Настройки групп
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_settings (
                    group_id BIGINT PRIMARY KEY,
                    is_enabled INTEGER DEFAULT 1,
                    allow_all_members INTEGER DEFAULT 1,
                    show_stats INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Групповые долги
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_debts (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    debtor_id BIGINT NOT NULL,
                    debtor_name TEXT,
                    creditor_id BIGINT NOT NULL,
                    creditor_name TEXT,
                    amount REAL NOT NULL,
                    description TEXT,
                    is_settled INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error initializing database: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)

    def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Добавить пользователя"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id, username, first_name))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding user: {e}")
        finally:
            cursor.close()
            self.return_connection(conn)

    def _normalize_date(self, date_value):
        """Нормализация даты"""
        if isinstance(date_value, datetime):
            return date_value
        if isinstance(date_value, str):
            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        return None

    def add_expense(self, user_id, amount, category, description=None, date=None):
        """Добавить расход"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            normalized = self._normalize_date(date)

            if normalized:
                cursor.execute("""
                    INSERT INTO expenses (user_id, amount, category, description, date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, amount, category, description, normalized))
            else:
                cursor.execute("""
                    INSERT INTO expenses (user_id, amount, category, description)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, amount, category, description))

            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding expense: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)

    def add_income(self, user_id, amount, source, description=None, date=None):
        """Добавить доход"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            normalized = self._normalize_date(date)

            if normalized:
                cursor.execute("""
                    INSERT INTO income (user_id, amount, source, description, date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, amount, source, description, normalized))
            else:
                cursor.execute("""
                    INSERT INTO income (user_id, amount, source, description)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, amount, source, description))

            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding income: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)

    def add_expenses_bulk(self, user_id: int, entries: List[Dict]) -> int:
        """Массовое добавление расходов"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            inserted = 0
            
            for entry in entries:
                try:
                    date_value = entry.get('date')
                    cursor.execute("""
                        INSERT INTO expenses (user_id, amount, category, description, date)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        entry['amount'],
                        entry['category'],
                        entry.get('description'),
                        date_value if date_value else datetime.now()
                    ))
                    inserted += 1
                except Exception as e:
                    logger.error(f"Error inserting bulk expense: {e}")
                    continue
            
            conn.commit()
            return inserted
        except Exception as e:
            conn.rollback()
            logger.error(f"Error in bulk expense insert: {e}")
            return 0
        finally:
            cursor.close()
            self.return_connection(conn)

    def add_income_bulk(self, user_id: int, entries: List[Dict]) -> int:
        """Массовое добавление доходов"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            inserted = 0
            
            for entry in entries:
                try:
                    date_value = entry.get('date')
                    cursor.execute("""
                        INSERT INTO income (user_id, amount, source, description, date)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        entry['amount'],
                        entry['source'],
                        entry.get('description'),
                        date_value if date_value else datetime.now()
                    ))
                    inserted += 1
                except Exception as e:
                    logger.error(f"Error inserting bulk income: {e}")
                    continue
            
            conn.commit()
            return inserted
        except Exception as e:
            conn.rollback()
            logger.error(f"Error in bulk income insert: {e}")
            return 0
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_expenses(self, user_id: int, days: int = None) -> List[Dict]:
        """Получить расходы"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            if days:
                date_from = datetime.now() - timedelta(days=days)
                cursor.execute("""
                    SELECT * FROM expenses
                    WHERE user_id = %s AND date >= %s
                    ORDER BY date DESC
                """, (user_id, date_from))
            else:
                cursor.execute("""
                    SELECT * FROM expenses
                    WHERE user_id = %s
                    ORDER BY date DESC
                """, (user_id,))

            result = [dict(row) for row in cursor.fetchall()]
            return result
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_income(self, user_id: int, days: int = None) -> List[Dict]:
        """Получить доходы"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            if days:
                date_from = datetime.now() - timedelta(days=days)
                cursor.execute("""
                    SELECT * FROM income
                    WHERE user_id = %s AND date >= %s
                    ORDER BY date DESC
                """, (user_id, date_from))
            else:
                cursor.execute("""
                    SELECT * FROM income
                    WHERE user_id = %s
                    ORDER BY date DESC
                """, (user_id,))

            result = [dict(row) for row in cursor.fetchall()]
            return result
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_last_expenses(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получить последние расходы"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM expenses
                WHERE user_id = %s
                ORDER BY date DESC
                LIMIT %s
            """, (user_id, limit))
            
            result = [dict(row) for row in cursor.fetchall()]
            return result
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_last_income(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получить последние доходы"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM income
                WHERE user_id = %s
                ORDER BY date DESC
                LIMIT %s
            """, (user_id, limit))
            
            result = [dict(row) for row in cursor.fetchall()]
            return result
        finally:
            cursor.close()
            self.return_connection(conn)

    def delete_expense(self, user_id: int, expense_id: int) -> bool:
        """Удалить расход"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM expenses WHERE id = %s AND user_id = %s
            """, (expense_id, user_id))

            conn.commit()
            deleted = cursor.rowcount > 0
            return deleted
        finally:
            cursor.close()
            self.return_connection(conn)

    def delete_income(self, user_id: int, income_id: int) -> bool:
        """Удалить доход"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM income WHERE id = %s AND user_id = %s
            """, (income_id, user_id))

            conn.commit()
            deleted = cursor.rowcount > 0
            return deleted
        finally:
            cursor.close()
            self.return_connection(conn)

    def delete_expenses_bulk(self, user_id: int, ids: List[int]) -> int:
        """Массовое удаление расходов"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM expenses 
                WHERE user_id = %s AND id = ANY(%s)
            """, (user_id, ids))
            
            conn.commit()
            deleted = cursor.rowcount
            return deleted
        finally:
            cursor.close()
            self.return_connection(conn)

    def delete_income_bulk(self, user_id: int, ids: List[int]) -> int:
        """Массовое удаление доходов"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM income 
                WHERE user_id = %s AND id = ANY(%s)
            """, (user_id, ids))
            
            conn.commit()
            deleted = cursor.rowcount
            return deleted
        finally:
            cursor.close()
            self.return_connection(conn)

    def search_transactions(self, user_id: int, query: str, 
                          txn_type: str = "all", limit: int = 15) -> Dict:
        """Поиск транзакций"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            results = {"expenses": [], "income": []}
            
            search_pattern = f"%{query}%"
            
            if txn_type in ("all", "expenses"):
                cursor.execute("""
                    SELECT * FROM expenses
                    WHERE user_id = %s 
                    AND (LOWER(category) LIKE LOWER(%s) 
                         OR LOWER(description) LIKE LOWER(%s))
                    ORDER BY date DESC
                    LIMIT %s
                """, (user_id, search_pattern, search_pattern, limit))
                results["expenses"] = [dict(row) for row in cursor.fetchall()]
            
            if txn_type in ("all", "income"):
                cursor.execute("""
                    SELECT * FROM income
                    WHERE user_id = %s 
                    AND (LOWER(source) LIKE LOWER(%s) 
                         OR LOWER(description) LIKE LOWER(%s))
                    ORDER BY date DESC
                    LIMIT %s
                """, (user_id, search_pattern, search_pattern, limit))
                results["income"] = [dict(row) for row in cursor.fetchall()]
            
            return results
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_statistics(self, user_id: int, days: int = None) -> Dict:
        """Получить статистику"""
        expenses = self.get_expenses(user_id, days)
        income = self.get_income(user_id, days)
        
        total_expenses = sum(e['amount'] for e in expenses)
        total_income = sum(i['amount'] for i in income)
        
        expenses_by_category = {}
        for exp in expenses:
            cat = exp['category']
            expenses_by_category[cat] = expenses_by_category.get(cat, 0) + exp['amount']
        
        income_by_source = {}
        for inc in income:
            src = inc['source']
            income_by_source[src] = income_by_source.get(src, 0) + inc['amount']
        
        return {
            'total_expenses': total_expenses,
            'total_income': total_income,
            'balance': total_income - total_expenses,
            'expenses_count': len(expenses),
            'income_count': len(income),
            'expenses': expenses,
            'income': income,
            'expenses_by_category': expenses_by_category,
            'income_by_source': income_by_source
        }

    def close_all_connections(self):
        """Закрыть все соединения"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("All connections closed")