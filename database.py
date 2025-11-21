import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union

class Database:
    def __init__(self, db_name: str = "finance.db"):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                source TEXT NOT NULL,
                description TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_user_date ON income(user_id, date)')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        conn.commit()
        conn.close()
    
    def _normalize_date(self, date_value: Optional[Union[datetime, str]]) -> Optional[str]:
        if isinstance(date_value, datetime):
            return date_value.isoformat()
        if isinstance(date_value, str):
            return date_value
        return None
    
    def add_expense(self, user_id: int, amount: float, category: str, description: str = None, date: Optional[Union[datetime, str]] = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        normalized_date = self._normalize_date(date)
        if normalized_date:
            cursor.execute('''
                INSERT INTO expenses (user_id, amount, category, description, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, category, description, normalized_date))
        else:
            cursor.execute('''
                INSERT INTO expenses (user_id, amount, category, description)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, category, description))
        conn.commit()
        conn.close()
    
    def add_expenses_bulk(self, user_id: int, entries: List[Dict]) -> int:
        if not entries:
            return 0
        conn = self.get_connection()
        cursor = conn.cursor()
        inserted = 0
        for entry in entries:
            normalized_date = self._normalize_date(entry.get('date'))
            amount = entry['amount']
            category = entry['category']
            description = entry.get('description')
            if normalized_date:
                cursor.execute('''
                    INSERT INTO expenses (user_id, amount, category, description, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, amount, category, description, normalized_date))
            else:
                cursor.execute('''
                    INSERT INTO expenses (user_id, amount, category, description)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, amount, category, description))
            inserted += 1
        conn.commit()
        conn.close()
        return inserted

    def add_income(self, user_id: int, amount: float, source: str, description: str = None, date: Optional[Union[datetime, str]] = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        normalized_date = self._normalize_date(date)
        if normalized_date:
            cursor.execute('''
                INSERT INTO income (user_id, amount, source, description, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, source, description, normalized_date))
        else:
            cursor.execute('''
                INSERT INTO income (user_id, amount, source, description)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, source, description))
        conn.commit()
        conn.close()

    def add_income_bulk(self, user_id: int, entries: List[Dict]) -> int:
        if not entries:
            return 0
        conn = self.get_connection()
        cursor = conn.cursor()
        inserted = 0
        for entry in entries:
            normalized_date = self._normalize_date(entry.get('date'))
            amount = entry['amount']
            source = entry['source']
            description = entry.get('description')
            if normalized_date:
                cursor.execute('''
                    INSERT INTO income (user_id, amount, source, description, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, amount, source, description, normalized_date))
            else:
                cursor.execute('''
                    INSERT INTO income (user_id, amount, source, description)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, amount, source, description))
            inserted += 1
        conn.commit()
        conn.close()
        return inserted
    
    def get_expenses(self, user_id: int, days: int = None) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if days:
            if days == 1:
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                yesterday = today - timedelta(days=1)
                date_from = yesterday
                date_to = today
                cursor.execute('''
                    SELECT * FROM expenses
                    WHERE user_id = ? AND date >= ? AND date < ?
                    ORDER BY date DESC
                ''', (user_id, date_from, date_to))
            else:
                date_from = datetime.now() - timedelta(days=days)
                cursor.execute('''
                    SELECT * FROM expenses
                    WHERE user_id = ? AND date >= ?
                    ORDER BY date DESC
                ''', (user_id, date_from))
        else:
            cursor.execute('''
                SELECT * FROM expenses
                WHERE user_id = ?
                ORDER BY date DESC
            ''', (user_id,))
        
        expenses = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return expenses
    
    def get_income(self, user_id: int, days: int = None) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if days:
            if days == 1:
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                yesterday = today - timedelta(days=1)
                date_from = yesterday
                date_to = today
                cursor.execute('''
                    SELECT * FROM income
                    WHERE user_id = ? AND date >= ? AND date < ?
                    ORDER BY date DESC
                ''', (user_id, date_from, date_to))
            else:
                date_from = datetime.now() - timedelta(days=days)
                cursor.execute('''
                    SELECT * FROM income
                    WHERE user_id = ? AND date >= ?
                    ORDER BY date DESC
                ''', (user_id, date_from))
        else:
            cursor.execute('''
                SELECT * FROM income
                WHERE user_id = ?
                ORDER BY date DESC
            ''', (user_id,))
        
        income = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return income
    
    def get_statistics(self, user_id: int, days: int) -> Dict:
        expenses = self.get_expenses(user_id, days)
        income = self.get_income(user_id, days)
        
        total_expenses = sum(e['amount'] for e in expenses)
        total_income = sum(i['amount'] for i in income)
        balance = total_income - total_expenses
        
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
            'balance': balance,
            'expenses_count': len(expenses),
            'income_count': len(income),
            'expenses_by_category': expenses_by_category,
            'income_by_source': income_by_source,
            'expenses': expenses,
            'income': income
        }
    
    def get_last_expenses(self, user_id: int, limit: int = 10) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (user_id, limit))
        expenses = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return expenses
    
    def get_last_income(self, user_id: int, limit: int = 10) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM income
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (user_id, limit))
        income = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return income

    def delete_expense(self, user_id: int, expense_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?', (expense_id, user_id))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def delete_income(self, user_id: int, income_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM income WHERE id = ? AND user_id = ?', (income_id, user_id))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def delete_expenses_bulk(self, user_id: int, expense_ids: List[int]) -> int:
        if not expense_ids:
            return 0
        conn = self.get_connection()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(expense_ids))
        query = f'DELETE FROM expenses WHERE user_id = ? AND id IN ({placeholders})'
        cursor.execute(query, [user_id, *expense_ids])
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        return deleted
    
    def delete_income_bulk(self, user_id: int, income_ids: List[int]) -> int:
        if not income_ids:
            return 0
        conn = self.get_connection()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(income_ids))
        query = f'DELETE FROM income WHERE user_id = ? AND id IN ({placeholders})'
        cursor.execute(query, [user_id, *income_ids])
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        return deleted

    def search_transactions(self, user_id: int, query: str, txn_type: str = "all", limit: int = 10) -> Dict[str, List[Dict]]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        pattern = f"%{query.lower()}%"
        
        expenses = []
        income = []
        
        if txn_type in ("all", "expenses"):
            cursor.execute('''
                SELECT * FROM expenses
                WHERE user_id = ? AND (
                    LOWER(category) LIKE ? OR
                    (description IS NOT NULL AND LOWER(description) LIKE ?)
                )
                ORDER BY date DESC
                LIMIT ?
            ''', (user_id, pattern, pattern, limit))
            expenses = [dict(row) for row in cursor.fetchall()]
        
        if txn_type in ("all", "income"):
            cursor.execute('''
                SELECT * FROM income
                WHERE user_id = ? AND (
                    LOWER(source) LIKE ? OR
                    (description IS NOT NULL AND LOWER(description) LIKE ?)
                )
                ORDER BY date DESC
                LIMIT ?
            ''', (user_id, pattern, pattern, limit))
            income = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return {"expenses": expenses, "income": income}
