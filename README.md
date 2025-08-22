# FNOL Claims Processing System

A React-based First Notice Of Loss (FNOL) claims processing system with AI-powered complexity analysis using AWS Bedrock and Strands Agents, plus browser automation capabilities using Nova Act.

## Features

- **Claims Queue Management**: View and manage insurance claims in queue and detailed views
- **AI-Powered Complexity Analysis**: Uses AWS Bedrock with Claude 3.7 Sonnet to analyze claim complexity
- **Automated Status Updates**: Claims are automatically routed to "Needs Review" or "Resolved" based on complexity
- **Browser Automation**: Nova Act for intelligent browser automation
- **Real-time Updates**: Dynamic UI updates based on claim status changes

## Architecture

- **Frontend**: React.js application with responsive design
- **Backend**: FastAPI serving both the React app and API endpoints
- **AI Agent**: Strands Agents with AWS Bedrock for complexity analysis
- **Automation**: Nova Act for intelligent browser automation

## Prerequisites

- Python 3.8+
- Node.js 16+
- AWS CLI configured with appropriate permissions
- Chrome browser (for automation)
- AWS Bedrock access in us-west-2 region

## Setup Instructions

### 1. Initial Setup

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup script
./setup.sh
```

### 2. Manual Setup (if needed)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies and build React app
cd frontend
npm install
npm run build
cd ..
```

### 3. AWS Configuration

Ensure your AWS credentials are configured:

```bash
aws configure
# Set region to us-west-2
export AWS_DEFAULT_REGION=us-west-2
```

### 4. Start the Application

```bash
# Make start script executable
chmod +x start.sh

# Start the application
./start.sh
```

The application will be available at `http://localhost:8000`

## Usage

### Web Interface

1. **Queue View**: See all active claims in a compact card format
2. **Detailed View**: Click "Detailed View" to see comprehensive claim information
3. **Analyze Claims**: In detailed view, click "Analyze Complexity" on any claim
4. **Status Updates**: Claims automatically update status based on AI analysis

### Browser Automation with Nova Act

#### Setup Browser Automation

```bash
cd browser_automate

# Make setup script executable
chmod +x setup_automation.sh

# Run automation setup
./setup_automation.sh
```

#### Run Nova Act Automation

```bash
cd browser_automate
source automation_venv/bin/activate

# Basic automation
python automate_claims.py

# Headless mode (no browser window)
python automate_claims.py --headless

# Record video of automation
python automate_claims.py --record_video

# Custom base URL
python automate_claims.py --base_url http://localhost:3000
```

#### Nova Act Features

- **Context Switching**: Uses `with NovaAct()` context manager
- **Natural Language**: Commands in plain English
- **Schema Validation**: Structured data extraction with Pydantic
- **Video Recording**: Optional automation recording
- **Headless Mode**: Background automation without UI

## API Endpoints

- `GET /api/claims` - Get all active claims
- `GET /api/claims/{claim_id}` - Get specific claim details
- `POST /api/analyze-claim` - Analyze claim complexity

## Claim Types

The system handles various claim types:

### Property Claims
- Wind/Hail Damage
- Fire Damage
- Water Damage
- Flood Damage

### Vehicle Claims
- Collision
- Theft
- Comprehensive

## Complexity Analysis

The AI agent analyzes claims based on:

1. **Damage Amount**: Higher amounts increase complexity
2. **Evidence Volume**: More evidence requires detailed review
3. **Claim Type**: Certain types (fire, theft) are inherently complex
4. **Historical Patterns**: Learning from past claim resolutions

### Analysis Tools

The Strands agent uses these tools:

- `analyze_damage_amount`: Evaluates financial impact
- `analyze_evidence_volume`: Assesses evidence complexity
- `analyze_claim_type`: Determines type-based complexity

## File Structure

```
browser_automate_fnol/
├── main.py                     # FastAPI application
├── complexity_analyzer.py      # Strands agent for AI analysis
├── requirements.txt            # Python dependencies
├── setup.sh                   # Setup script
├── start.sh                   # Start script
├── README.md                  # This file
├── frontend/                  # React application
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.js
│       ├── App.css
│       └── index.js
└── browser_automate/          # Browser automation
    ├── requirements.txt
    ├── setup_automation.sh
    └── automate_claims.py     # Nova Act automation
```

## Sample Claims Data

The system includes 5 sample claims:

1. **CLM-001**: Property - Wind/Hail Damage ($15,000)
2. **CLM-002**: Vehicle - Collision ($8,500)
3. **CLM-003**: Property - Fire Damage ($45,000)
4. **CLM-004**: Vehicle - Theft ($25,000)
5. **CLM-005**: Property - Water Damage ($12,000)

## Troubleshooting

### Common Issues

1. **AWS Permissions**: Ensure Bedrock access in us-west-2
2. **Node.js Build**: Run `npm run build` in frontend directory
3. **Chrome Driver**: Install ChromeDriver for automation
4. **Port Conflicts**: Ensure port 8000 is available

### Logs

Check console output for:
- FastAPI server logs
- Strands agent responses
- Browser automation status

## Development

### Adding New Claim Types

1. Update sample data in `main.py`
2. Add complexity rules in `complexity_analyzer.py`
3. Update UI components in `frontend/src/App.js`

### Customizing AI Analysis

Modify the system prompt and tools in `complexity_analyzer.py`:

```python
system_prompt = """Your custom analysis instructions..."""
tools = [your_custom_tools]
```

## Security Notes

- No sensitive data in code examples
- AWS credentials managed via AWS CLI
- Environment variables for configuration
- Input validation on all API endpoints

## License

This project is for demonstration purposes. Ensure compliance with your organization's policies when using in production.


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.