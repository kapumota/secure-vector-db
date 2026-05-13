FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SECURE_VECTOR_DB_PATH=/data/secure_vector_db.sqlite \
    SECURE_VECTOR_DB_API_KEY=change-me-in-production

WORKDIR /app

COPY requirements.txt pyproject.toml README.md API.md ./
COPY secure_vector_db ./secure_vector_db

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

CMD ["uvicorn", "secure_vector_db.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
