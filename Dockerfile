FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy engine code
COPY engine/ ./engine/

# Expose ports
EXPOSE 5000 5001 5002

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=engine/rest_api.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')"

# Default command: start Flask API
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "engine.rest_api:create_api_server()"]
