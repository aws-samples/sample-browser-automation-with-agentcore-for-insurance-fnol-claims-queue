# Hands-Free First Notice of Loss (FNOL): Agentic Intake with Browser Automation

**Companion repository for the AWS blog post:** *Hands-free first notice of loss: Using Strands Agents and AgentCore Browser Automation for intelligent claims intake*

This repository demonstrates how to automate insurance FNOL intake by combining **Strands Agents on Amazon Bedrock** for domain reasoning with **AgentCore Browser Automation** for live portal interaction—eliminating repetitive screen work while preserving human expertise and auditability.

## What This Solution Does

Manual FNOL processing consumes significant expert time on repetitive tasks. Claims professionals spend 30–40% of their time validating evidence completeness, navigating portals, and interpreting unstructured artifacts before meaningful assessment can begin.

This solution automates that mechanical work by:

- **Analyzing multimodal evidence at ingestion**: Images, videos, and audio transcripts are evaluated and tagged using codified insurance business rules
- **Classifying claim complexity**: Evidence-derived signals determine routing and escalation needs before downstream processing
- **Automating portal interaction**: AgentCore Browser Automation navigates the FNOL queue, triggers analysis, and observes UI state—without brittle scripts or selectors
- **Preserving full auditability**: Every action, screenshot, and decision is captured as part of a traceable execution trail

The result: claims professionals receive context-rich, pre-analyzed submissions ready for judgment rather than validation.

## Architecture Overview

The solution separates concerns across four layers:

1. **Browser Automation Layer**: AgentCore Browser Automation observes and interacts with the FNOL portal using Chrome DevTools Protocol (CDP)
2. **Domain Reasoning Layer**: Strands Agents on Amazon Bedrock apply insurance-specific business rules to interpret evidence and assess complexity
3. **Application Runtime**: FNOL portal and backend services run as containerized applications on Amazon ECS with AWS Fargate
4. **Persistence & Observability**: Evidence stored in Amazon S3, claim state in Amazon DynamoDB, execution logs in Amazon CloudWatch

**Key architectural principle**: Browser automation handles UI orchestration (when and where to act), while Strands Agents handle domain reasoning (what the evidence means).

## Prerequisites

- **AWS Account** with permissions for CDK, ECS, S3, DynamoDB, ALB, CloudFront, and IAM
- **AWS CLI** configured with credentials
- **CDK CLI**: `npm install -g aws-cdk`
- **Python 3.12** for local scripts (evidence generation, data seeding, browser automation)
- **NOVA_ACT_API_KEY**: Required for AgentCore Browser Automation (export as environment variable)

## Deployment

### Step 1: Deploy Infrastructure and Application

```bash
# Clone the repository
git clone https://github.com/pkamra/sample-browser-automation-with-agentcore-for-insurance-fnol-claims-queue.git
cd sample-browser-automation-with-agentcore-for-insurance-fnol-claims-queue

# Deploy to AWS (provisions infrastructure and deploys containerized app)
./deploy.sh
```

The deployment creates:
- **DynamoDB Table**: `ClaimsEvidence`
- **S3 Bucket**: `claims-evidencestore-<account>-<region>`
- **ECS Service**: Containerized FNOL portal and backend on Fargate
- **CloudFront Distribution**: Public-facing URL for the FNOL portal

**Note the CloudFront URL** from the deployment output—you'll need it for browser automation.

Wait 2–3 minutes for the ECS service to become healthy before proceeding.

### Step 2: Generate Evidence (Optional)

Generate synthetic claim evidence using Amazon Nova models:

```bash
cd utils
python3.12 -m venv utils_venv
source utils_venv/bin/activate
pip install -r requirements.txt

# Example: Generate evidence for a wind/hail damage claim
python3 generate_claim_evidence.py \
  "Wind hail damage roof damage from hailstorm call by John Smith with Policy number POL-12345 Claim number CLM-001" \
  all --images 5 --videos 2 --transcripts 1
```

### Step 3: Seed the Database

Populate the DynamoDB table with initial claims data:

```bash
cd backend
export CLAIMS_TABLE_NAME=ClaimsEvidence
export EVIDENCE_BUCKET_NAME=claims-evidencestore-<account>-<region>
python3 seed_data.py
```

### Step 4: Run Browser Automation

Set up and execute the agentic FNOL intake workflow:

```bash
cd full_automation
python3.12 -m venv automation_venv
source automation_venv/bin/activate
pip install -r requirements.txt

# Configure environment
export NOVA_ACT_API_KEY=your-nova-act-api-key-here
export CLOUDFRONT_URL=https://<your-cloudfront-distribution>.cloudfront.net

# Initialize browser environment and run automation
python3 setup_browser_environment.py
python3 run_claims_automation_fixed.py
```

The automation will:
1. Navigate to the FNOL queue
2. Select unprocessed claims
3. Trigger evidence analysis (images, videos, audio)
4. Classify claim complexity
5. Generate structured notes

**Execution artifacts** (screenshots, logs, metadata) are saved in `full_automation/screenshots/` for audit and troubleshooting.

## How It Works

### Evidence Analysis

When the automation invokes **Analyze Images**, **Analyze Videos**, or **Analyze Audio**, Strands Agents apply codified business rules to:

- Identify what each artifact depicts (damage type, perspective, relevance)
- Assess quality and usability
- Tag evidence with structured attributes
- Detect missing or insufficient artifacts

### Complexity Classification

After evidence is tagged, the agent evaluates the claim holistically by combining:

- Severity indicators across modalities
- Evidence completeness and consistency
- Policy thresholds for escalation

Claims are classified as **SIMPLE**, **MEDIUM**, or **COMPLEX**, with structured notes explaining the rationale.

### Auditability

Every browser interaction is captured:
- **Screenshots** at each decision point
- **Prompts and decisions** as structured metadata
- **UI state transitions** via Chrome DevTools Protocol

This produces a complete execution trail showing what the agent saw, why it acted, and what conclusions were derived.

## Key Benefits

- **Reduced intake time**: Automated evidence validation eliminates 30–40% of manual screen work
- **Consistent interpretation**: Codified business rules ensure uniform evidence evaluation
- **Early gap detection**: Missing or insufficient artifacts identified at ingestion
- **Improved routing**: Claims triaged based on actual evidence, not intake assumptions
- **Durable data asset**: Tagged evidence becomes queryable, reusable across the claim lifecycle
- **No portal changes required**: Works with existing systems via browser-level automation

## Troubleshooting

**DynamoDB Access Denied**: Verify ECS task role has DynamoDB permissions  
**Claims Not Loading**: Check CloudWatch logs for ECS service errors  
**Bedrock Analysis Fails**: Ensure region is set to `us-west-2`  
**Browser Automation Fails**: Verify `NOVA_ACT_API_KEY` and `CLOUDFRONT_URL` are set correctly

### View Logs

```bash
# ECS service logs
aws logs tail /ecs/claims-app --follow

# Browser automation logs
cat full_automation/screenshots/<session-id>/execution.log
```

## Related Resources

- **Blog Post**: *Hands-free first notice of loss: Using Strands Agents and AgentCore Browser Automation for intelligent claims intake*
- **Strands Agents Documentation**: [Amazon Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- **AgentCore Browser Automation**: Contact AWS for access and documentation

## License

This sample code is made available under the MIT-0 license. See the LICENSE file.
