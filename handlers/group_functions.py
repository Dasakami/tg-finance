from psycopg2.extras import RealDictCursor
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from utils import format_currency
from datetime import datetime, timedelta

db = Database()


class GroupFinance:
    """Класс для управления групповыми финансами"""
    
    def __init__(self):
        pass
    
    def add_group_expense(self, group_id: int, user_id: int, user_name: str,
                         amount: float, category: str, description: str = None) -> bool:
        """Добавить групповой расход"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO group_expenses (group_id, user_id, user_name, amount, category, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (group_id, user_id, user_name, amount, category, description))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error adding group expense: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_group_statistics(self, group_id: int, days: int = 30) -> Dict:
        """Получить статистику группы"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            date_from = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT * FROM group_expenses
                WHERE group_id = %s AND date >= %s
                ORDER BY date DESC
            ''', (group_id, date_from))
            
            expenses = [dict(row) for row in cursor.fetchall()]
            
            total = sum(e['amount'] for e in expenses)

            by_user = {}
            for exp in expenses:
                user = exp['user_name'] or f"User {exp['user_id']}"
                by_user[user] = by_user.get(user, 0) + exp['amount']
            
            by_category = {}
            for exp in expenses:
                cat = exp['category']
                by_category[cat] = by_category.get(cat, 0) + exp['amount']
            
            return {
                'total': total,
                'count': len(expenses),
                'by_user': by_user,
                'by_category': by_category,
                'expenses': expenses
            }
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def add_debt(self, group_id: int, debtor_id: int, debtor_name: str,
                creditor_id: int, creditor_name: str, amount: float, 
                description: str = None) -> bool:
        """Добавить долг"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO group_debts 
                (group_id, debtor_id, debtor_name, creditor_id, creditor_name, amount, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (group_id, debtor_id, debtor_name, creditor_id, creditor_name, amount, description))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error adding debt: {e}")
            return False
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def get_user_debts(self, group_id: int, user_id: int) -> Dict:
        """Получить долги пользователя"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('''
                SELECT * FROM group_debts
                WHERE group_id = %s AND debtor_id = %s AND is_settled = 0
            ''', (group_id, user_id))
            owes = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('''
                SELECT * FROM group_debts
                WHERE group_id = %s AND creditor_id = %s AND is_settled = 0
            ''', (group_id, user_id))
            owed = [dict(row) for row in cursor.fetchall()]
            
            total_owes = sum(d['amount'] for d in owes)
            total_owed = sum(d['amount'] for d in owed)
            
            return {
                'owes': owes,
                'owed': owed,
                'total_owes': total_owes,
                'total_owed': total_owed,
                'balance': total_owed - total_owes
            }
        finally:
            cursor.close()
            db.return_connection(conn)
    
    def settle_debt(self, debt_id: int) -> bool:
        """Погасить долг"""
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE group_debts
                SET is_settled = 1
                WHERE id = %s
            ''', (debt_id,))
            
            conn.commit()
            settled = cursor.rowcount > 0
            return settled
        finally:
            cursor.close()
            db.return_connection(conn)


group_finance = GroupFinance()

async def group_add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Добавить групповой расход
    Команда: /group_expense 500 еда пицца
    """
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Эта команда работает только в группах!")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Формат: /group_expense СУММА КАТЕГОРИЯ [описание]\n"
            "Пример: /group_expense 500 еда пицца на всех"
        )
        return
    
    try:
        amount = float(context.args[0].replace(',', '.'))
        category = context.args[1]
        description = ' '.join(context.args[2:]) if len(context.args) > 2 else None
        
        user = update.effective_user
        group_id = update.effective_chat.id
        
        success = group_finance.add_group_expense(
            group_id=group_id,
            user_id=user.id,
            user_name=user.first_name,
            amount=amount,
            category=category,
            description=description
        )
        
        if success:
            db.add_expense(user.id, amount, category, description)
            
            await update.message.reply_text(
                f"✅ Групповой расход добавлен!\n\n"
                f"👤 {user.first_name}\n"
                f"💰 {format_currency(amount)} руб.\n"
                f"📂 {category}\n" +
                (f"📝 {description}" if description else "")
            )
        else:
            await update.message.reply_text("❌ Ошибка при добавлении расхода")
            
    except ValueError:
        await update.message.reply_text("Неверная сумма! Используй число.")


async def group_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать групповую статистику
    Команда: /group_stats [дни]
    """
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Эта команда работает только в группах!")
        return
    
    days = 30
    if context.args:
        try:
            days = int(context.args[0])
            days = max(1, min(days, 90)) 
        except ValueError:
            pass
    
    group_id = update.effective_chat.id
    stats = group_finance.get_group_statistics(group_id, days)
    
    if stats['count'] == 0:
        await update.message.reply_text(
            f"За последние {days} дней в группе не было расходов.\n"
            "Используй /group_expense для добавления!"
        )
        return
    
    message = f"📊 <b>Групповая статистика за {days} дней</b>\n\n"
    message += f"💸 Всего потрачено: {format_currency(stats['total'])} руб.\n"
    message += f"📝 Операций: {stats['count']}\n\n"
    
    if stats['by_user']:
        message += "👥 <b>По участникам:</b>\n"
        for user, amount in sorted(stats['by_user'].items(), key=lambda x: x[1], reverse=True)[:5]:
            message += f"  • {user}: {format_currency(amount)} руб.\n"
        message += "\n"

    if stats['by_category']:
        message += "📂 <b>По категориям:</b>\n"
        for cat, amount in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True)[:5]:
            message += f"  • {cat}: {format_currency(amount)} руб.\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def group_add_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Добавить долг
    Команда: /group_debt @username 500 за пиццу
    """
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Эта команда работает только в группах!")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Формат: /group_debt @username СУММА [описание]\n"
            "Пример: /group_debt @john 500 за пиццу"
        )
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Ответь на сообщение человека, которому ты должен, "
            "или укажи @username"
        )
        return
    
    try:
        amount = float(context.args[1].replace(',', '.'))
        description = ' '.join(context.args[2:]) if len(context.args) > 2 else None
        
        debtor = update.effective_user
        creditor = update.message.reply_to_message.from_user
        group_id = update.effective_chat.id
        
        success = group_finance.add_debt(
            group_id=group_id,
            debtor_id=debtor.id,
            debtor_name=debtor.first_name,
            creditor_id=creditor.id,
            creditor_name=creditor.first_name,
            amount=amount,
            description=description
        )
        
        if success:
            await update.message.reply_text(
                f"✅ Долг зафиксирован!\n\n"
                f"💸 {debtor.first_name} → {creditor.first_name}\n"
                f"💰 {format_currency(amount)} руб.\n" +
                (f"📝 {description}" if description else "")
            )
        else:
            await update.message.reply_text("❌ Ошибка при добавлении долга")
            
    except (ValueError, IndexError):
        await update.message.reply_text("Неверный формат! Проверь команду.")


async def group_my_debts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать мои долги в группе
    Команда: /group_my_debts
    """
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Эта команда работает только в группах!")
        return
    
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    
    debts = group_finance.get_user_debts(group_id, user_id)
    
    message = "💰 <b>Твои долги в группе</b>\n\n"
    
    if debts['owes']:
        message += "💸 <b>Ты должен:</b>\n"
        for debt in debts['owes']:
            message += f"  • {debt['creditor_name']}: {format_currency(debt['amount'])} руб."
            if debt['description']:
                message += f" ({debt['description']})"
            message += f" [ID: {debt['id']}]\n"
        message += f"<b>Итого должен:</b> {format_currency(debts['total_owes'])} руб.\n\n"
    
    if debts['owed']:
        message += "💵 <b>Тебе должны:</b>\n"
        for debt in debts['owed']:
            message += f"  • {debt['debtor_name']}: {format_currency(debt['amount'])} руб."
            if debt['description']:
                message += f" ({debt['description']})"
            message += f" [ID: {debt['id']}]\n"
        message += f"<b>Итого должны:</b> {format_currency(debts['total_owed'])} руб.\n\n"
    
    if not debts['owes'] and not debts['owed']:
        message += "У тебя нет долгов! 🎉"
    else:
        balance = debts['balance']
        if balance > 0:
            message += f"💚 <b>Твой баланс: +{format_currency(balance)} руб.</b>"
        elif balance < 0:
            message += f"🔴 <b>Твой баланс: {format_currency(balance)} руб.</b>"
        else:
            message += "💙 <b>Ты в балансе!</b>"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def group_settle_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Погасить долг
    Команда: /group_settle ID
    """
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Эта команда работает только в группах!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Формат: /group_settle ID\n"
            "Посмотри ID долгов командой /group_my_debts"
        )
        return
    
    try:
        debt_id = int(context.args[0])
        
        if group_finance.settle_debt(debt_id):
            await update.message.reply_text("✅ Долг погашен!")
        else:
            await update.message.reply_text("❌ Долг не найден")
            
    except ValueError:
        await update.message.reply_text("Неверный ID!")


async def group_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь по групповым командам"""
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Эта команда работает только в группах!")
        return
    
    message = (
        "🤖 <b>Групповые команды</b>\n\n"
        "📝 <b>Расходы:</b>\n"
        "/group_expense СУММА КАТЕГОРИЯ [описание]\n"
        "Пример: /group_expense 500 еда пицца\n\n"
        "📊 <b>Статистика:</b>\n"
        "/group_stats [дни] - статистика группы\n\n"
        "💰 <b>Долги:</b>\n"
        "/group_debt @user СУММА [описание] - добавить долг\n"
        "/group_my_debts - мои долги\n"
        "/group_settle ID - погасить долг\n\n"
        "💡 <b>Inline режим:</b>\n"
        "В любом чате используй:\n"
        "@вашбот расход 500 еда\n"
        "@вашбот доход 5000 зарплата"
    )
    
    await update.message.reply_text(message, parse_mode='HTML')


__all__ = [
    'group_add_expense',
    'group_statistics',
    'group_add_debt',
    'group_my_debts',
    'group_settle_debt',
    'group_help'
]