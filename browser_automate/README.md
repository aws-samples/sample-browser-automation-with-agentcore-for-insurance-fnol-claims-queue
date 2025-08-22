# FNOL Claims Browser Automation with Nova Act

This directory contains browser automation scripts for the FNOL Claims Processing System using AWS Nova Act. Nova Act is an intelligent browser automation framework that uses natural language commands to interact with web applications.

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Key Components](#key-components)
- [How It Works](#how-it-works)
- [Usage Examples](#usage-examples)
- [Extending Functionality](#extending-functionality)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

The browser automation system automatically processes FNOL claims by:

1. **Navigating** to the FNOL Claims application
2. **Switching** to detailed view to see full claim information
3. **Analyzing** each claim using AI-powered complexity analysis
4. **Handling** analysis results and status updates
5. **Verifying** that claims have been processed correctly

### Why Nova Act?

- **Natural Language**: Commands written in plain English
- **AI-Powered**: Understands context and adapts to UI changes
- **AWS Integration**: Built for AWS environments with proper IAM support
- **Schema Validation**: Structured data extraction with Pydantic models
- **Video Recording**: Built-in automation recording capabilities

## Setup

### Prerequisites

- Python 3.8+
- AWS CLI configured with appropriate permissions
- FNOL Claims application running (default: http://localhost:8000)
- AWS Bedrock access in us-west-2 region

### Installation

```bash
# Navigate to browser automation directory
cd browser_automate

# Make setup script executable
chmod +x setup_automation.sh

# Run setup (creates virtual environment and installs dependencies)
./setup_automation.sh

# Activate the environment
source automation_venv/bin/activate
```

### Dependencies

The automation uses these key packages:

- **nova-act**: AWS Nova Act framework for intelligent browser automation
- **boto3**: AWS SDK for Python (used by Nova Act)
- **requests**: HTTP library for API calls to get claim data
- **fire**: Command-line interface framework
- **pydantic**: Data validation and schema modeling

## Key Components

### 1. Main Automation Script (`automate_claims.py`)

The primary automation script with these key functions:

```python
def get_claims_from_api(base_url: str) -> List[dict]:
    """Fetches new claims from the FNOL API"""

def main(base_url: str, headless: bool, record_video: bool) -> None:
    """Main automation workflow using Nova Act context manager"""
```

### 2. Data Models

Pydantic models for structured data extraction:

```python
class ClaimStatus(BaseModel):
    claim_id: str
    status: str
    complexity: Optional[str] = None

class ClaimsStatusList(BaseModel):
    claims: List[ClaimStatus]
```

### 3. Setup Script (`setup_automation.sh`)

Automated environment setup with:
- Virtual environment creation
- Dependency installation
- AWS region configuration
- Usage instructions

## How It Works

### 1. Initialization Phase

```python
with NovaAct(
    starting_page=base_url,
    headless=headless,
    record_video=record_video,
) as nova:
```

Nova Act:
- Launches Chrome browser
- Navigates to the starting page
- Initializes AI-powered automation engine

### 2. View Switching

```python
nova.act(
    "Look for a button labeled 'Detailed View' at the top of the page and click it. "
    "This will switch from the queue view to a detailed view where I can see full claim information."
)
```

Nova Act uses computer vision and AI to:
- Locate the "Detailed View" button
- Click it to switch views
- Wait for the new view to load

### 3. Claim Processing Loop

For each claim, Nova Act:

```python
nova.act(
    f"Find the claim card with ID '{claim['id']}' on the page. "
    f"This is a {claim['type']} claim for {claim['subtype']} with ${claim['estimated_damage']:,} in estimated damage. "
    f"Look for the 'Analyze Complexity' button in this claim card and click it."
)
```

- **Identifies** the specific claim card using contextual information
- **Locates** the "Analyze Complexity" button
- **Clicks** the button to trigger AI analysis
- **Handles** the resulting alert dialog

### 4. Result Verification

```python
result = nova.act(
    "Look at all the claim cards on the page and tell me the status of each claim. "
    "Return the information as a list of claims with their IDs and current statuses.",
    schema=ClaimsStatusList.model_json_schema()
)
```

Nova Act:
- **Extracts** structured data from the page
- **Validates** against Pydantic schema
- **Returns** parsed claim status information

## Usage Examples

### Basic Automation

```bash
# Process all new claims with visible browser
python automate_claims.py
```

### Headless Automation

```bash
# Run automation in background (no browser window)
python automate_claims.py --headless
```

### Video Recording

```bash
# Record automation for documentation/debugging
python automate_claims.py --record_video
```

### Custom Environment

```bash
# Point to different environment
python automate_claims.py --base_url http://staging.example.com
```

### Combined Options

```bash
# Headless automation with video recording
python automate_claims.py --headless --record_video --base_url http://prod.example.com
```

## Extending Functionality

### Adding New Automation Tasks

1. **Create New Function**:

```python
def process_resolved_claims(nova: NovaAct) -> None:
    """Process claims that have been resolved"""
    nova.act(
        "Find all claims with 'Resolved' status and export them to a report. "
        "Look for an 'Export' or 'Download' button."
    )
```

2. **Add to Main Workflow**:

```python
def main(base_url: str, headless: bool = False, export_resolved: bool = False):
    with NovaAct(starting_page=base_url, headless=headless) as nova:
        # Existing automation...
        
        if export_resolved:
            process_resolved_claims(nova)
```

### Adding Data Extraction

1. **Define Pydantic Model**:

```python
class ClaimDetails(BaseModel):
    claim_id: str
    policy_holder: str
    estimated_damage: float
    evidence_count: int
    date_of_loss: str
```

2. **Extract Structured Data**:

```python
result = nova.act(
    "Extract detailed information from all visible claim cards",
    schema=ClaimDetails.model_json_schema()
)

if result.matches_schema:
    claim_details = ClaimDetails.model_validate(result.parsed_response)
```

### Adding Custom Workflows

1. **Create Workflow Function**:

```python
def custom_claim_workflow(nova: NovaAct, workflow_type: str) -> None:
    """Custom workflow based on claim type"""
    if workflow_type == "property":
        nova.act("Filter claims to show only Property claims")
    elif workflow_type == "vehicle":
        nova.act("Filter claims to show only Vehicle claims")
    
    nova.act("Sort claims by damage amount in descending order")
```

2. **Add CLI Option**:

```python
def main(
    base_url: str = "http://localhost:8000",
    headless: bool = False,
    workflow: str = "standard"  # New parameter
):
    with NovaAct(starting_page=base_url, headless=headless) as nova:
        if workflow != "standard":
            custom_claim_workflow(nova, workflow)
```

### Adding Error Handling

```python
def robust_claim_analysis(nova: NovaAct, claim_id: str, max_retries: int = 3) -> bool:
    """Analyze claim with retry logic"""
    for attempt in range(max_retries):
        try:
            nova.act(f"Find claim {claim_id} and click 'Analyze Complexity'")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
    return False
```

## Troubleshooting

### Common Issues

1. **Nova Act Initialization Fails**
   ```
   Error: Could not initialize Nova Act
   ```
   **Solution**: Check AWS credentials and region configuration
   ```bash
   aws configure list
   export AWS_DEFAULT_REGION=us-west-2
   ```

2. **Element Not Found**
   ```
   Error: Could not find element
   ```
   **Solution**: Make commands more descriptive
   ```python
   # Instead of:
   nova.act("Click button")
   
   # Use:
   nova.act("Find the blue 'Analyze Complexity' button in the claim card with ID 'CLM-001' and click it")
   ```

3. **Schema Validation Fails**
   ```
   Error: Response doesn't match schema
   ```
   **Solution**: Check the Pydantic model and make fields optional
   ```python
   class ClaimStatus(BaseModel):
       claim_id: str
       status: Optional[str] = None  # Make optional
   ```

4. **Timeout Issues**
   ```
   Error: Operation timed out
   ```
   **Solution**: Add explicit waits
   ```python
   nova.act("Click analyze button")
   time.sleep(5)  # Wait for processing
   nova.act("Handle the alert dialog")
   ```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run automation with debug info
python automate_claims.py --headless=False  # Keep browser visible
```

### Video Recording for Debugging

```bash
# Record automation to see what's happening
python automate_claims.py --record_video

# Video will be saved in the current directory
```

## Best Practices

### 1. Command Writing

**Good Commands**:
```python
nova.act(
    "Find the claim card with ID 'CLM-001' which shows a Property claim for Wind/Hail Damage. "
    "Look for the red 'Analyze Complexity' button in this specific card and click it."
)
```

**Avoid**:
```python
nova.act("Click analyze")  # Too vague
```

### 2. Error Handling

Always check for success and provide fallbacks:

```python
try:
    nova.act("Primary action")
except Exception as e:
    print(f"Primary action failed: {e}")
    nova.act("Fallback action")
```

### 3. Data Validation

Use Pydantic models for structured data:

```python
result = nova.act("Extract data", schema=MyModel.model_json_schema())
if result.matches_schema:
    data = MyModel.model_validate(result.parsed_response)
else:
    print(f"Invalid data: {result.parsed_response}")
```

### 4. Timing

Add appropriate waits for dynamic content:

```python
nova.act("Click button that triggers async operation")
time.sleep(3)  # Wait for operation to complete
nova.act("Handle the result")
```

### 5. Environment Configuration

Use environment variables for configuration:

```python
import os

base_url = os.getenv("FNOL_BASE_URL", "http://localhost:8000")
aws_region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
```

## Advanced Features

### Custom Browser Configuration

```python
from selenium.webdriver.chrome.options import Options

def main(base_url: str, custom_options: bool = False):
    chrome_options = None
    if custom_options:
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
    
    with NovaAct(
        starting_page=base_url,
        chrome_options=chrome_options
    ) as nova:
        # Automation logic
```

### Parallel Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

def process_claim_batch(claims_batch: List[dict]) -> None:
    """Process a batch of claims in parallel"""
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(process_single_claim, claim) 
            for claim in claims_batch
        ]
        for future in futures:
            future.result()
```

### Integration with CI/CD

```yaml
# GitHub Actions example
- name: Run Claims Automation
  run: |
    cd browser_automate
    source automation_venv/bin/activate
    python automate_claims.py --headless --base_url ${{ secrets.STAGING_URL }}
```

This automation framework provides a solid foundation for intelligent browser automation of the FNOL Claims system and can be easily extended for additional use cases.
