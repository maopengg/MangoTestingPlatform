#!/bin/bash

# Mango Service Startup Script

echo ""Starting Mango Service...""

# Activate virtual environment if it exists
if [ -d ""venv"" ]; then
    source venv/bin/activate
fi

# Install dependencies if requirements.txt is newer than installed packages
if [ ! -f requirements.lock ] || [ requirements.txt -nt requirements.lock ]; then
    echo ""Installing dependencies...""
    pip install -r requirements.txt
    pip freeze > requirements.lock
fi

# Run database migrations (if using alembic)
# alembic upgrade head

# Start the application
echo ""Starting FastAPI application...""
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

echo ""Mango Service stopped.""
