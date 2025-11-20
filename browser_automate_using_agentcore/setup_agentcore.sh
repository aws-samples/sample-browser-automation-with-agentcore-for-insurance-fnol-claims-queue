#!/bin/bash

echo "🚀 Setting up AgentCore Browser Automation Environment"

# Create virtual environment with Python 3.12
echo "📦 Creating virtual environment with Python 3.12..."
python3.12 -m venv agentcore_venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source agentcore_venv/bin/activate

# Install requirements
echo "📥 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To use:"
echo "1. source agentcore_venv/bin/activate"
echo "2. python agentcore_claims_automation.py"
echo ""
echo "Or with live viewer:"
echo "python agentcore_claims_with_viewer.py"
