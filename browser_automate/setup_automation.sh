#!/bin/bash

# Setup script for AgentCore Browser Tool with Nova Act
echo "Setting up AgentCore Browser Tool automation environment..."

# Create virtual environment for automation
python3 -m venv automation_venv
source automation_venv/bin/activate

# Install requirements (AgentCore will handle browser setup)
python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt

# Set AWS region and Nova Act API key
export AWS_DEFAULT_REGION=us-west-2
export NOVA_ACT_API_KEY='97e6365f-ca2d-44bd-9494-07b1361ee4c9'

# Test AgentCore and Nova Act installation
python -c "from bedrock_agentcore.tools.browser_client import browser_session; print('AgentCore Browser Tool OK')"
python -c "from nova_act import NovaAct; print('Nova Act OK')"

echo "✅ AgentCore Browser Tool automation setup complete!"
echo ""
echo "Usage examples:"
echo "1. Basic automation:"
echo "   source automation_venv/bin/activate"
echo "   python automate_claims.py"
echo "2. Headless mode:"
echo "   python automate_claims.py --headless"
echo "3. Record video:"
echo "   python automate_claims.py --record_video"
echo "4. Custom URL:"
echo "   python automate_claims.py --base_url http://localhost:3000"
echo ""
echo "Note: Make sure the claims application is running before starting automation"
