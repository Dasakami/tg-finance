import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import os


class Database:
    def __init__(self):
        self.conn_params = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }
        self.init_database()

    def get_connection(self):
        return psycopg2.connect(**self.conn_params)

    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

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

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (user_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_income_user_date ON income (user_id, date)")

        conn.commit()
        conn.close()

    def add_user(self, user_id: int, username: str = None, first_name: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id, username, first_name))

        conn.commit()
        conn.close()

    def _normalize_date(self, date_value):
        if isinstance(date_value, datetime):
            return date_value
        if isinstance(date_value, str):
            return datetime.fromisoformat(date_value)
        return None

    def add_expense(self, user_id, amount, category, description=None, date=None):
        conn = self.get_connection()
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
        conn.close()

    def add_income(self, user_id, amount, source, description=None, date=None):
        conn = self.get_connection()
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
        conn.close()

    def get_expenses(self, user_id: int, days: int = None) -> List[Dict]:
        conn = self.get_connection()
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

        result = cursor.fetchall()
        conn.close()
        return result

    def get_income(self, user_id: int, days: int = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if days:
            date_from = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT * FROM income
                WHERE user_id = %s AND date >= %s
                ORDER ORDER BY date DESC
            """, (user_id, date_from))
        else:
            cursor.execute("""
                SELECT * FROM income
                WHERE user_id = %s
                ORDER BY date DESC
            """, (user_id,))

        result = cursor.fetchall()
        conn.close()
        return result

    def delete_expense(self, user_id: int, expense_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM expenses WHERE id = %s AND user_id = %s
        """, (expense_id, user_id))

        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def delete_income(self, user_id: int, income_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM income WHERE id = %s AND user_id = %s
        """, (income_id, user_id))

        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
