#!/bin/bash

# Setup script for FNOL Claims App
echo "Setting up FNOL Claims Application with Python 3.12..."

# Remove existing virtual environment if it exists
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# Create virtual environment with Python 3.12
echo "Creating virtual environment with Python 3.12..."
python3.12 -m venv venv
source venv/bin/activate

# Upgrade pip first
echo "Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies from requirements.txt
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

# Check if frontend directory exists, if not create it
if [ ! -d "frontend" ]; then
    echo "Frontend directory not found, creating basic structure..."
    mkdir -p frontend/src frontend/public
fi

# Install Node.js dependencies for React (if package.json exists)
if [ -f "frontend/package.json" ]; then
    echo "Installing Node.js dependencies..."
    cd frontend
    npm install
    echo "Building React app..."
    npm run build
    cd ..
else
    echo "No package.json found, skipping Node.js setup"
fi

# Set AWS region
export AWS_DEFAULT_REGION=us-west-2

echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "1. source venv/bin/activate"
echo "2. ./start.sh"
echo ""
echo "Make sure you have:"
echo "- AWS CLI configured with Bedrock access"
echo "- AWS region set to us-west-2"
echo ""
echo "If strands-agents installation failed, check the documentation for proper installation method."
