FROM python:3.12.11-alpine3.22

WORKDIR /build
COPY pyproject.toml /build/pyproject.toml
COPY 03-Backend/src /build/03-Backend/src
RUN python -m pip install --no-cache-dir .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
