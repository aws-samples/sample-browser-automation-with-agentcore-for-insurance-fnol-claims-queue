#!/bin/bash

echo "🚀 Setting up Claims Automation System with AgentCore..."

# Backend setup
echo "📦 Setting up Python backend..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Frontend setup
echo "🌐 Setting up React frontend..."
cd frontend
npm install
cd ..

# Browser automation setup
echo "🤖 Setting up Nova Act browser automation..."
cd browser_automate
chmod +x setup_automation.sh
./setup_automation.sh
cd ..

echo "✅ Setup complete!"
echo ""
echo "🎯 To start the application:"
echo "1. Backend: source venv/bin/activate && python main.py"
echo "2. Frontend: cd frontend && npm start"
echo "3. Browser automation: cd browser_automate && source automation_venv/bin/activate && python automate_claims.py"
