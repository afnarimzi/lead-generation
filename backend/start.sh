#!/bin/bash

# Start the FastAPI backend server

# Activate virtual environment if it exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Start the server
echo "🚀 Starting FastAPI backend on http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""

python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
