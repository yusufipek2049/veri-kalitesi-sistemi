FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir . uvicorn==0.35.0

COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY scripts/run_dev.py /app/scripts/run_dev.py
COPY scripts/seed_database.py /app/scripts/seed_database.py

RUN useradd --create-home --uid 10001 appuser
USER appuser

CMD ["uvicorn", "scripts.run_dev:app", "--host", "0.0.0.0", "--port", "8000"]
