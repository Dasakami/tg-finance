# Базовый образ
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app
# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Команда запуска
CMD ["python", "bot.py"]
