# Используем лёгкий официальный образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники и тест
COPY step_orchestrator.py steps.yaml test_steps.py ./

# ✅ Запускаем тест с отображением логов в реальном времени
# Используем "python3 -u" (unbuffered mode) чтобы вывод шел сразу
# "set -euxo pipefail" — для прозрачности и надёжности сборки
RUN set -euxo pipefail && \
    echo "🚀 Запуск теста task_orchestrator..." && \
    python3 -u test_steps.py && \
    echo "✅ Тест успешно завершён!"

# ⏳ Контейнер остаётся живым (для Cline / отладки)
CMD ["sleep", "infinity"]
