# Cloud Deployment

Deploy the Claims Processing application to AWS with secure access controls.

## Architecture
```
Internet → CloudFront (WAF) → ALB → ECS Fargate Container
                ↑                      ↑
        IP Whitelist                Frontend + Backend
```

## Components
- **ECS Fargate**: Single container running both React frontend and FastAPI backend
- **ALB**: Application Load Balancer (private, only accessible via CloudFront)
- **CloudFront**: CDN distribution with caching and WAF protection
- **WAF**: Web Application Firewall with IP whitelist rules

## Folder Structure
```
cloud_deployment/
├── README.md                    # This file
├── backend/                     # FastAPI backend (copied from parent)
├── frontend/                    # React frontend (copied from parent)
├── Dockerfile                   # Container definition
├── .dockerignore               # Docker build exclusions
├── cdk/                        # AWS CDK infrastructure code
│   ├── app.py                  # CDK app entry point
│   ├── stacks/                 # CDK stack definitions
│   ├── requirements.txt        # CDK dependencies
│   └── cdk.json               # CDK configuration
└── automation/                 # Browser automation for cloud deployment
    ├── README.md              # Automation instructions
    ├── requirements.txt       # Automation dependencies
    ├── automate_claims_cloud.py # AgentCore automation script
    └── setup_cloud_automation.sh # Setup script
```

## Deployment Steps

### 1. Prerequisites
```bash
# Install AWS CDK
npm install -g aws-cdk

# Configure AWS credentials
aws configure
# OR
aws sso login --profile your-profile
```

### 2. Deploy Infrastructure
```bash
cd cdk
npm install

# Bootstrap CDK (one-time setup)
cdk bootstrap

# Deploy the stack
cdk deploy 
```

### 3. Get CloudFront URL
After deployment, note the CloudFront URL from CDK output.

**Security:** The WAF automatically whitelists your current IP address during deployment. Only your IP can access the CloudFront URL initially.

### 4. Update IP Whitelist
To add new IP addresses:
```bash
# Update the WAF IP set
aws wafv2 update-ip-set --scope CLOUDFRONT --id <ip-set-id> --addresses "1.2.3.4/32,5.6.7.8/32"
```

### 5. Run Automation
```bash
cd automation
./setup_cloud_automation.sh
export CLOUDFRONT_URL="https://d1b6akcz3bibhg.cloudfront.net"
python automate_claims_cloud.py --record
```

## Environment Variables
- `AWS_DEFAULT_REGION`: AWS region (e.g., us-west-2)
- `NOVA_ACT_API_KEY`: Nova Act API key for automation
- `CLOUDFRONT_URL`: The deployed application URL

## Security Features
- WAF with IP whitelist (only your deployment IP initially)
- ALB not directly accessible from internet
- CloudFront enforces HTTPS
- Container runs with minimal privileges

## Monitoring
- CloudWatch logs for container
- ALB access logs
- CloudFront access logs
- WAF blocked request logs
