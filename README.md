# Claims Automation System with AgentCore

A comprehensive insurance claims automation system using AgentCore Browser Tool and Nova Act for intelligent browser automation.

## 🏗️ Architecture

- **Frontend**: React application for claims management interface
- **Backend**: FastAPI server with complexity analysis
- **Automation**: Nova Act browser automation with AgentCore integration
- **Analysis**: ML-powered complexity scoring for claims triage

## 🚀 Setup (One-time)

```bash
# Clone and setup everything
cd /Users/rishikamra/dev/browser_new
chmod +x setup.sh
./setup.sh
```

## 🧪 Testing Steps (Proper Order)

### Step 1: Start Backend API
```bash
# Terminal 1
cd /Users/rishikamra/dev/browser_new
source venv/bin/activate
python main.py
```
**Expected**: Server running on http://localhost:8000

### Step 2: Start Frontend
```bash
# Terminal 2
cd /Users/rishikamra/dev/browser_new/frontend
npm start
```
**Expected**: Frontend running on http://localhost:3000

### Step 3: Test Browser Automation
```bash
# Terminal 3
cd /Users/rishikamra/dev/browser_new/browser_automate
source automation_venv/bin/activate
python automate_claims_simple.py
```

### Step 4: Test Backend API Only (Alternative)
```bash
# If frontend issues, test backend directly
cd /Users/rishikamra/dev/browser_new/browser_automate
source automation_venv/bin/activate
python automate_backend_api.py
```

## 🔧 Components

### Backend API Endpoints
- `GET /api/claims` - Claims data
- `POST /analyze-complexity` - ML complexity analysis
- `GET /` - Frontend static files

### Browser Automation Scripts
- `automate_claims_simple.py` - Basic Nova Act automation
- `automate_backend_api.py` - API-only testing (no frontend needed)
- `automate_claims_with_viewer.py` - Enhanced with live view

### Configuration
- **Nova Act API Key**: `ABCDKEY`
- **AWS Region**: `us-west-2`

## 🎯 Quick Test Commands

```bash
# Test backend API
curl http://localhost:8000/api/claims

# Test complexity analyzer
curl -X POST http://localhost:8000/analyze-complexity \
  -H "Content-Type: application/json" \
  -d '{"claim_amount": 15000, "description": "Vehicle collision", "injury_severity": "moderate"}'

# Test frontend
open http://localhost:3000
```

## 🐛 Troubleshooting

### Frontend Proxy Errors
- **Issue**: `Proxy error: Could not proxy request`
- **Fix**: Start backend first, then frontend

### Nova Act Connection Refused
- **Issue**: `Connection refused by https://localhost:3000`
- **Fix**: Ensure frontend is running on http://localhost:3000

### Module Not Found
- **Issue**: `ModuleNotFoundError: No module named 'bedrock_agentcore'`
- **Fix**: Use `automate_backend_api.py` for testing without AgentCore

## 📊 Expected Results

1. **Backend**: JSON API responses with claims data
2. **Frontend**: React interface showing claims queue
3. **Automation**: Console output showing claim processing steps
4. **Complexity Analysis**: ML scores and recommendations

## 🔒 Security

- Isolated browser automation sessions
- API key management via environment variables
- CORS enabled for frontend integration
