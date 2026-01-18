FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash mango && chown -R mango:mango /app
USER mango

EXPOSE 8000

CMD [""uvicorn"", ""src.main:app"", ""--host"", ""0.0.0.0"", ""--port"", ""8000""]
