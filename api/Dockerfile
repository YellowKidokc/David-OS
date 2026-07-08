FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FIHUB_DB_PATH=/data/top-of-mind.sqlite3

WORKDIR /app

COPY pyproject.toml README.md ./
COPY file_intelligence_hub ./file_intelligence_hub
COPY config ./config
COPY schemas ./schemas

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN mkdir -p /data

EXPOSE 10000

CMD ["fihub-api", "--host", "0.0.0.0", "--port", "10000"]
