# ══════════════════════════════════════════════════════════
# PRIZM Backend - Python FastAPI Dockerfile
# ══════════════════════════════════════════════════════════
FROM python:3.11-slim
# Set working directory
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
# Copy requirements first for better caching
COPY requirements.txt .
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy Python application files
COPY python/ .
COPY frontend/ /frontend/
# Create non-root user
RUN useradd -m -u 1001 python && \
    chown -R python:python /app /frontend
USER python
# Expose port (now 8000 to match frontend expectations)
EXPOSE 8000
# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"
# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
