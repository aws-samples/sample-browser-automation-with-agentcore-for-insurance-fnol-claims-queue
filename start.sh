#!/bin/bash

# Start script for FNOL Claims App
echo "Starting FNOL Claims Application..."

# Activate virtual environment
source venv/bin/activate

# Set AWS region
export AWS_DEFAULT_REGION=us-west-2

# Start the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
