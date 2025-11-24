# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Устанавливаем системные зависимости (оптимально, минимум)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements для кеширования слоёв
COPY requirements.txt .

# Устанавливаем зависимости в отдельную директорию
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Stage 2: Final image ----
FROM python:3.12-slim

WORKDIR /app

# Копируем установленные библиотеки из builder
COPY --from=builder /install /usr/local

# Копируем проект
COPY . .

# Устанавливаем UTF-8, чтобы не было проблем с русским
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Понижаем размер образа
RUN apt-get purge -y build-essential || true

# Команда запуска
CMD ["python", "bot.py"]
