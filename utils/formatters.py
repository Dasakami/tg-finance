from datetime import datetime, timedelta
from typing import Optional

def format_currency(amount: float) -> str:
    return f"{amount:,.2f}".replace(',', ' ').replace('.', ',')

def format_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%d.%m.%Y %H:%M')
    except:
        return date_str

def parse_user_date(text: str) -> Optional[datetime]:
    if not text:
        return None
    cleaned = text.strip().lower()
    if cleaned in ("/today", "сегодня", "today"):
        return datetime.now()
    if cleaned in ("/yesterday", "вчера", "yesterday"):
        return datetime.now() - timedelta(days=1)
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None

