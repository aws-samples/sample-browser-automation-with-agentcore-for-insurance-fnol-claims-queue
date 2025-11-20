# ngrok Setup for AgentCore Browser Automation

This guide helps you expose your local claims application to the internet so AgentCore Browser (running in AWS) can access it.

## 🚀 Quick Setup

### Step 1: Install ngrok
```bash
brew install ngrok
```

### Step 2: Create ngrok Account
1. Go to https://ngrok.com
2. Sign up for a free account
3. Verify your email

### Step 3: Get Auth Token
1. Go to https://dashboard.ngrok.com/get-started/your-authtoken
2. Copy your auth token (looks like: `2abc123def456ghi789jkl`)
2ztcoa8KspAQeRQ2MwckWCDo9rU_461aYVWfxGjx9JttnsdXP

### Step 4: Configure ngrok
```bash
ngrok config add-authtoken 2ztcoa8KspAQeRQ2MwckWCDo9rU_461aYVWfxGjx9JttnsdXP
```
Replace `YOUR_AUTH_TOKEN_HERE` with your actual token from Step 3.

### Step 5: Start Your Applications

**Terminal 1 - Backend:**
```bash
cd /Users/rishikamra/dev/browser_new
source venv/bin/activate
python main.py
```
Wait for: `INFO: Uvicorn running on http://127.0.0.1:8000`

**Terminal 2 - Frontend:**
```bash
cd /Users/rishikamra/dev/browser_new/frontend
npm start
```
Wait for: `Local: http://localhost:3000`

**Terminal 3 - ngrok:**
```bash
ngrok http 3000
```

### Step 6: Copy ngrok URL
From Terminal 3, copy the HTTPS URL that looks like:
```
Forwarding    https://abc123-def456.ngrok.io -> http://localhost:3000
```

Copy: `https://abc123-def456.ngrok.io`

### Step 7: Update Automation Script
Edit `agentcore_claims_automation.py` and replace:
```python
def automate_claims_with_agentcore(base_url="https://YOUR-NGROK-URL.ngrok.io"):
```

With your actual ngrok URL:
```python
def automate_claims_with_agentcore(base_url="https://abc123-def456.ngrok.io"):
```

### Step 8: Run AgentCore Automation

**Terminal 4 - Automation:**
```bash
cd /Users/rishikamra/dev/browser_new/browser_automate_using_agentcore
source agentcore_venv/bin/activate
python agentcore_claims_automation.py
```

## 🔧 Troubleshooting

**"tunnel session failed: Your account is limited to 1 simultaneous ngrok agent session"**
- Free accounts get 1 tunnel. Stop any other ngrok processes first.

**"ERR_NGROK_108"**
- Your auth token is invalid. Re-run Step 4 with correct token.

**"Connection refused"**
- Make sure your frontend is running on localhost:3000 first.

**ngrok URL changes every restart**
- Free accounts get random URLs. Update your script each time you restart ngrok.
- Upgrade to paid plan for static domains.

## 📝 Complete Terminal Setup

You need **4 terminals running**:

1. **Backend** (port 8000): `python main.py`
2. **Frontend** (port 3000): `npm start`  
3. **ngrok** (tunnel): `ngrok http 3000`
4. **Automation**: `python agentcore_claims_automation.py`

## ✅ Success Indicators

- Backend: Shows "Uvicorn running on http://127.0.0.1:8000"
- Frontend: Shows "Local: http://localhost:3000"
- ngrok: Shows "Forwarding https://xxx.ngrok.io -> http://localhost:3000"
- Automation: Shows "✅ AgentCore browser session created"

Your local claims app is now accessible to AgentCore Browser in AWS! 🎉
