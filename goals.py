"""
Система финансовых целей и накоплений
"""
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import Database

db = Database()


class GoalsManager:
    """Управление финансовыми целями"""
    
    def __init__(self):
        self._init_tables()
    
    def _init_tables(self):
        """Инициализация таблиц"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS financial_goals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    goal_name TEXT NOT NULL,
                    target_amount REAL NOT NULL,
                    current_amount REAL DEFAULT 0,
                    deadline TIMESTAMP,
                    icon TEXT,
                    description TEXT,
                    is_completed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goal_contributions (
                    id SERIAL PRIMARY KEY,
                    goal_id INTEGER NOT NULL,
                    user_id BIGINT NOT NULL,
                    amount REAL NOT NULL,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (goal_id) REFERENCES financial_goals (id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error initializing goals tables: {e}")
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def create_goal(self, user_id: int, goal_name: str, target_amount: float,
                   deadline: datetime = None, icon: str = None, description: str = None) -> bool:
        """Создать новую цель"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO financial_goals 
                (user_id, goal_name, target_amount, deadline, icon, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, goal_name, target_amount, deadline, icon, description))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error creating goal: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_goals(self, user_id: int, include_completed: bool = False) -> List[Dict]:
        """Получить список целей"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if include_completed:
                cursor.execute("""
                    SELECT * FROM financial_goals
                    WHERE user_id = %s
                    ORDER BY is_completed ASC, created_at DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT * FROM financial_goals
                    WHERE user_id = %s AND is_completed = 0
                    ORDER BY created_at DESC
                """, (user_id,))
            
            goals = [dict(row) for row in cursor.fetchall()]
            for goal in goals:
                goal['progress'] = (goal['current_amount'] / goal['target_amount'] * 100) if goal['target_amount'] > 0 else 0
                goal['remaining'] = goal['target_amount'] - goal['current_amount']
                
                if goal['deadline']:
                    deadline = goal['deadline']
                    if isinstance(deadline, str):
                        deadline = datetime.fromisoformat(deadline)
                    days_left = (deadline - datetime.now()).days
                    goal['days_left'] = max(0, days_left)
                else:
                    goal['days_left'] = None
            
            return goals
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def contribute_to_goal(self, goal_id: int, user_id: int, amount: float, note: str = None) -> bool:
        """Внести деньги в цель"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO goal_contributions (goal_id, user_id, amount, note)
                VALUES (%s, %s, %s, %s)
            """, (goal_id, user_id, amount, note))
            
            cursor.execute("""
                UPDATE financial_goals
                SET current_amount = current_amount + %s
                WHERE id = %s AND user_id = %s
            """, (amount, goal_id, user_id))
            
            cursor.execute("""
                SELECT current_amount, target_amount FROM financial_goals
                WHERE id = %s
            """, (goal_id,))
            
            row = cursor.fetchone()
            if row and row[0] >= row[1]:
                cursor.execute("""
                    UPDATE financial_goals
                    SET is_completed = 1, completed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (goal_id,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error contributing to goal: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_goal_contributions(self, goal_id: int, limit: int = 20) -> List[Dict]:
        """Получить историю взносов"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM goal_contributions
                WHERE goal_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (goal_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def delete_goal(self, goal_id: int, user_id: int) -> bool:
        """Удалить цель"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM financial_goals
                WHERE id = %s AND user_id = %s
            """, (goal_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting goal: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_goal_summary(self, user_id: int) -> Dict:
        """Сводка по всем целям"""
        goals = self.get_goals(user_id, include_completed=False)
        completed_goals = self.get_goals(user_id, include_completed=True)
        completed_goals = [g for g in completed_goals if g['is_completed']]
        
        total_target = sum(g['target_amount'] for g in goals)
        total_saved = sum(g['current_amount'] for g in goals)
        total_remaining = sum(g['remaining'] for g in goals)
        
        return {
            'active_goals': len(goals),
            'completed_goals': len(completed_goals),
            'total_target': total_target,
            'total_saved': total_saved,
            'total_remaining': total_remaining,
            'overall_progress': (total_saved / total_target * 100) if total_target > 0 else 0
        }


goals_manager = GoalsManager()