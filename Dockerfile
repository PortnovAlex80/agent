FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Кладём основной скрипт и (опционально) пример steps.yaml.
COPY task_orchestrator.py /app/task_orchestrator.py
COPY steps.yaml /app/steps.yaml

# Живём вечно, чтобы Cline мог делать docker exec -i ...
CMD ["sleep", "infinity"]
