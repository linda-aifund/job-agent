FROM python:3.12-slim

# System dependencies for lxml, psycopg2, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create dirs for uploads and data
RUN mkdir -p /app/uploads /app/data

ENV PORT=8000
ENV UPLOAD_DIR=/app/uploads

EXPOSE $PORT

CMD alembic upgrade head && uvicorn job_agent.web.app:app --host 0.0.0.0 --port $PORT
