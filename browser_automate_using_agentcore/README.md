# Claims Automation with AgentCore Browser Tool

This folder contains automation scripts using **Amazon Bedrock AgentCore Browser Tool** as described in the [AWS blog post](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-browser-tool/).

## 🏗️ Architecture

```
AgentCore Browser Session (us-west-2)
    ↓
Nova Act (with CDP endpoint)
    ↓
Claims Application (localhost:3000)
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
cd /Users/rishikamra/dev/browser_new/browser_automate_using_agentcore
./setup_agentcore.sh
```

### 2. Activate Environment
```bash
source agentcore_venv/bin/activate
```

### 3. Run Automation

**Basic automation:**
```bash
python agentcore_claims_automation.py
```

**With live viewer:**
```bash
python agentcore_claims_with_viewer.py
```

## 📁 Files

- `agentcore_claims_automation.py` - Main automation script using AgentCore
- `agentcore_claims_with_viewer.py` - Automation with live browser viewer
- `setup_agentcore.sh` - Environment setup script
- `requirements.txt` - Python dependencies

## 🔧 Key Features

### AgentCore Browser Tool Benefits:
- **AWS-managed browser sessions** in us-west-2
- **Better reliability** with managed infrastructure
- **CDP endpoint integration** with Nova Act
- **Scalable browser automation**

### Automation Features:
- Processes claims automatically
- Switches between Queue/Detailed views
- Analyzes claim complexity
- Handles modal dialogs properly
- Live viewer option for monitoring

## 🆚 Comparison with Nova Act Only

| Feature | Nova Act Only | AgentCore + Nova Act |
|---------|---------------|---------------------|
| Browser Management | Local browser | AWS-managed browser |
| Reliability | Good | Better |
| Scalability | Limited | High |
| Setup Complexity | Simple | Moderate |
| Live Viewing | Direct browser | Optional viewer server |

## 🎯 Usage

Make sure your claims application is running:
```bash
# Terminal 1 - Backend
cd /Users/rishikamra/dev/browser_new
source venv/bin/activate
python main.py

# Terminal 2 - Frontend  
cd /Users/rishikamra/dev/browser_new/frontend
npm start

# Terminal 3 - AgentCore Automation
cd /Users/rishikamra/dev/browser_new/browser_automate_using_agentcore
source agentcore_venv/bin/activate
python agentcore_claims_automation.py
```
