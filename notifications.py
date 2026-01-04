"""
Система умных уведомлений и напоминаний
"""
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import Database
from utils import format_currency

db = Database()


class NotificationManager:
    """Управление умными уведомлениями"""
    
    def __init__(self):
        self._init_tables()
    
    def _init_tables(self):
        """Инициализация таблиц"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_settings (
                    user_id BIGINT PRIMARY KEY,
                    daily_summary INTEGER DEFAULT 1,
                    weekly_report INTEGER DEFAULT 1,
                    budget_alerts INTEGER DEFAULT 1,
                    large_expense_alert INTEGER DEFAULT 1,
                    large_expense_threshold REAL DEFAULT 5000,
                    regular_expense_reminders INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS regular_expenses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    frequency TEXT NOT NULL,
                    last_reminder TIMESTAMP,
                    next_reminder TIMESTAMP,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    notification_type TEXT NOT NULL,
                    message TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error initializing notifications: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_settings(self, user_id: int) -> Dict:
        """Получить настройки уведомлений"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM notification_settings WHERE user_id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                self._create_default_settings(user_id)
                return self.get_settings(user_id)
            
            return dict(row)
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def _create_default_settings(self, user_id: int):
        """Создать настройки по умолчанию"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notification_settings (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))
            conn.commit()
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def update_settings(self, user_id: int, **kwargs) -> bool:
        """Обновить настройки уведомлений"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            fields = []
            values = []
            for key, value in kwargs.items():
                fields.append(f"{key} = %s")
                values.append(value)
            
            if not fields:
                return False
            
            values.append(user_id)
            
            query = f"""
                UPDATE notification_settings
                SET {', '.join(fields)}
                WHERE user_id = %s
            """
            
            cursor.execute(query, values)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error updating notification settings: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def check_large_expense(self, user_id: int, amount: float) -> Optional[str]:
        """Проверить, является ли трата крупной"""
        settings = self.get_settings(user_id)
        
        if not settings['large_expense_alert']:
            return None
        
        threshold = settings['large_expense_threshold']
        
        if amount >= threshold:
            return (
                f"⚠️ <b>Крупная трата!</b>\n\n"
                f"Сумма {format_currency(amount)} руб. превышает порог в {format_currency(threshold)} руб.\n\n"
                "💡 Это запланированная трата?"
            )
        
        return None
    
    def add_regular_expense(self, user_id: int, category: str, amount: float,
                           frequency: str, description: str = None) -> bool:
        """
        Добавить регулярную трату
        
        Args:
            frequency: 'daily', 'weekly', 'monthly'
        """
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            now = datetime.now()
            if frequency == 'daily':
                next_reminder = now + timedelta(days=1)
            elif frequency == 'weekly':
                next_reminder = now + timedelta(weeks=1)
            elif frequency == 'monthly':
                next_reminder = now + timedelta(days=30)
            else:
                next_reminder = now + timedelta(days=7)
            
            cursor.execute("""
                INSERT INTO regular_expenses 
                (user_id, category, amount, frequency, next_reminder, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, category, amount, frequency, next_reminder, description))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error adding regular expense: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_regular_expenses(self, user_id: int) -> List[Dict]:
        """Получить список регулярных трат"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM regular_expenses
                WHERE user_id = %s AND is_active = 1
                ORDER BY next_reminder
            """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_pending_reminders(self, user_id: int) -> List[Dict]:
        """Получить напоминания, которые нужно отправить"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM regular_expenses
                WHERE user_id = %s 
                AND is_active = 1 
                AND next_reminder <= CURRENT_TIMESTAMP
            """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def mark_reminder_sent(self, expense_id: int):
        """Отметить напоминание как отправленное"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT frequency FROM regular_expenses WHERE id = %s
            """, (expense_id,))
            
            row = cursor.fetchone()
            if not row:
                return
            
            frequency = row[0]
            
            now = datetime.now()
            if frequency == 'daily':
                next_reminder = now + timedelta(days=1)
            elif frequency == 'weekly':
                next_reminder = now + timedelta(weeks=1)
            elif frequency == 'monthly':
                next_reminder = now + timedelta(days=30)
            else:
                next_reminder = now + timedelta(days=7)
            
            cursor.execute("""
                UPDATE regular_expenses
                SET last_reminder = CURRENT_TIMESTAMP,
                    next_reminder = %s
                WHERE id = %s
            """, (next_reminder, expense_id))
            
            conn.commit()
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def disable_regular_expense(self, expense_id: int) -> bool:
        """Отключить регулярную трату"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE regular_expenses
                SET is_active = 0
                WHERE id = %s
            """, (expense_id,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error disabling regular expense: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def generate_daily_summary(self, user_id: int) -> str:
        """Сгенерировать ежедневную сводку"""
        stats = db.get_statistics(user_id, 1)
        
        message = "📊 <b>Сводка за сегодня</b>\n\n"
        
        if stats['expenses_count'] > 0 or stats['income_count'] > 0:
            message += f"💸 Расходы: {format_currency(stats['total_expenses'])} руб.\n"
            message += f"💰 Доходы: {format_currency(stats['total_income'])} руб.\n"
            message += f"💵 Баланс дня: {format_currency(stats['balance'])} руб.\n\n"
            
            if stats['expenses_by_category']:
                message += "📂 Топ категории:\n"
                top_cats = sorted(stats['expenses_by_category'].items(), 
                                key=lambda x: x[1], reverse=True)[:3]
                for cat, amount in top_cats:
                    message += f"  • {cat}: {format_currency(amount)} руб.\n"
        else:
            message += "Сегодня не было операций.\n"
        
        message += "\n💡 Продолжай вести учёт!"
        
        return message
    
    def generate_weekly_report(self, user_id: int) -> str:
        """Сгенерировать недельный отчёт"""
        stats = db.get_statistics(user_id, 7)
        
        message = "📈 <b>Отчёт за неделю</b>\n\n"
        message += f"💸 Расходы: {format_currency(stats['total_expenses'])} руб.\n"
        message += f"💰 Доходы: {format_currency(stats['total_income'])} руб.\n"
        message += f"💵 Баланс недели: {format_currency(stats['balance'])} руб.\n\n"
        
        if stats['expenses_count'] > 0:
            avg_daily = stats['total_expenses'] / 7
            message += f"📊 Средние траты в день: {format_currency(avg_daily)} руб.\n\n"
        
        if stats['expenses_by_category']:
            message += "🏆 Топ-5 категорий расходов:\n"
            top_cats = sorted(stats['expenses_by_category'].items(), 
                            key=lambda x: x[1], reverse=True)[:5]
            for i, (cat, amount) in enumerate(top_cats, 1):
                percent = (amount / stats['total_expenses'] * 100) if stats['total_expenses'] > 0 else 0
                message += f"{i}. {cat}: {format_currency(amount)} руб. ({percent:.0f}%)\n"
        
        return message


notification_manager = NotificationManager()