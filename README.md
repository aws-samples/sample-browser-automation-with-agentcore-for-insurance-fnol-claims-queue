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
- **Node.js** (for CDK)
- **CDK CLI**: `npm install -g aws-cdk`
- **Python 3.12** for local scripts (evidence generation, data seeding, browser automation)
- **NOVA_ACT_API_KEY**: Required for AgentCore Browser Automation. Obtain from [nova.amazon.com/act](https://nova.amazon.com/act) using your amazon.com account (separate from AWS credentials)

## Deployment

### Step 1: Deploy Infrastructure and Application

```bash
# Clone the repository
git clone https://github.com/pkamra/sample-browser-automation-with-agentcore-for-insurance-fnol-claims-queue.git
cd sample-browser-automation-with-agentcore-for-insurance-fnol-claims-queue

# Configure AWS credentials (if using SSO)
export AWS_PROFILE=<your-profile-name>
aws sso login
# Verify credentials
aws sts get-caller-identity

# Deploy to AWS (provisions infrastructure and deploys containerized app)
./deploy.sh
```

The deployment deploys to your configured AWS region (defaults to `us-east-1`). It creates:
- **DynamoDB Table**: `Claims`
- **S3 Bucket**: `claims-evidence-<account>-<region>`
- **ECS Service**: Containerized FNOL portal and backend on Fargate
- **CloudFront Distribution**: Public-facing URL for the FNOL portal

**Note the CloudFront URL** from the deployment output—you'll need it for browser automation.

Wait 2–3 minutes for the ECS service to become healthy before proceeding.

### Step 2: Generate Evidence (Optional)

Generate synthetic claim evidence using Amazon Nova models. Pre-generated evidence for all 5 sample claims is included in `utils/generated_evidence/`. You only need to regenerate if you want fresh or different evidence.

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

Populate the DynamoDB table with initial claims data and upload evidence to S3:

```bash
# From the repository root
cd backend
export CLAIMS_TABLE_NAME=Claims
export EVIDENCE_BUCKET_NAME=claims-evidence-<account>-<region>
export AWS_DEFAULT_REGION=<region>  # Must match your deployment region
python3 seed_data.py
```

The seed script inserts 5 sample claims (CLM-001 through CLM-005), uploads evidence files from `utils/generated_evidence/` to S3, and links the S3 URLs to each claim in DynamoDB.

### Step 4: Run Browser Automation

Set up and execute the agentic FNOL intake workflow:

```bash
# From the repository root
cd full_automation
python3.12 -m venv automation_venv
source automation_venv/bin/activate
pip install -r requirements.txt

# Configure environment
export NOVA_ACT_API_KEY=your-nova-act-api-key-here
export CLOUDFRONT_URL=https://<your-cloudfront-distribution>.cloudfront.net
export AWS_DEFAULT_REGION=<region>  # Must match your deployment region

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

**Execution artifacts** are saved in `full_automation/screenshots/<session-id>/` for each run:
- Screenshots captured at each browser interaction step
- `execution.log` with prompts, agent decisions, and timing
- Session metadata for correlating with AgentCore console

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
**Bedrock Analysis Fails**: Ensure your deployment region supports the Bedrock models used (Claude Sonnet)  
**Browser Automation Fails**: Verify `NOVA_ACT_API_KEY` and `CLOUDFRONT_URL` are set correctly. If `setup_browser_environment.py` fails on role validation, wait a few seconds and retry (IAM propagation delay).  
**Region Mismatch**: Ensure `AWS_DEFAULT_REGION` matches the region where you deployed. The browser automation, seed script, and CDK stack must all target the same region.

### View Logs

```bash
# ECS service logs
aws logs tail /ecs/claims-app --follow

# Browser automation logs
cat full_automation/screenshots/<session-id>/execution.log
```

## Related Resources

- **Blog Post**: *Hands-free first notice of loss: Using Strands Agents and AgentCore Browser Automation for intelligent claims intake*
- **Amazon Nova Act**: [nova.amazon.com/act](https://nova.amazon.com/act)
- **Strands Agents**: [strandsagents.com](https://strandsagents.com/latest/)
- **AgentCore Browser Documentation**: [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-tool.html)

## License

This sample code is made available under the MIT-0 license. See the LICENSE file.
