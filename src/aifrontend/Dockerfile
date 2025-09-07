FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (including templates and static files)
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/

EXPOSE 5005

# Start with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5005", "app:app"]
