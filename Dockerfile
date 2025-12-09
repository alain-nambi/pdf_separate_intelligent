FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Create virtual environment
RUN python -m venv venv
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY run.py .
COPY worker.py .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app/uploads /app/output \
    && chown -R app:app /app
USER app

# Expose port for API
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["python", "run.py"]
