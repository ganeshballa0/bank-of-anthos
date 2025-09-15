# Dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (including templates/)
COPY . .

# Expose the app port
EXPOSE 8080

# Use Gunicorn and the app factory
# If your main module filename differs from app.py, update "app:create_app()"
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:create_app()"]
