#!/bin/bash

# Setup script for Nova Act browser automation
echo "Setting up Nova Act browser automation environment..."

# Create virtual environment for automation
python3.12 -m venv automation_venv
source automation_venv/bin/activate

# Install requirements (Nova Act will handle browser setup)
python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt

# Set AWS region for Nova Act
export AWS_DEFAULT_REGION=us-west-2
export NOVA_ACT_API_KEY='97e6365f-ca2d-44bd-9494-07b1361ee4c9'

# 6) smoke test
python -c "from nova_act import NovaAct; print('NovaAct OK')"

echo "✅ Nova Act automation setup complete!"
echo ""
echo "Usage examples:"
echo "1. Basic automation:"
echo "   first do source automation_venv/bin/activate"
echo "   python automate_claims.py"
echo "2. Headless mode:"
echo "   python automate_claims.py --headless"
echo ""
echo "3. Record video:"
echo "   python automate_claims.py --record_video"
echo ""
echo "4. Custom URL:"
echo "   python automate_claims.py --base_url http://localhost:3000"
echo ""
echo "Note: Make sure the FNOL application is running before starting automation"
