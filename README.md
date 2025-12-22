# Claims Processing Cloud Deployment

A cloud-native insurance claims processing system using AWS services with DynamoDB for persistent data storage.

## 🏗️ Architecture

- **Frontend**: React application served via CloudFront
- **Backend**: FastAPI on ECS Fargate with DynamoDB integration
- **Database**: DynamoDB for claims data persistence
- **AI/ML**: Amazon Bedrock with agents for complexity analysis
- **Security**: WAF protection and CloudFront-only ALB access

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.12 (for local scripts: evidence generation, data seeding, browser automation)
- CDK CLI: `npm install -g aws-cdk`
- **NOVA_ACT_API_KEY**: Required for browser automation (export as environment variable)

## 🚀 Deployment

```bash
# Clone and deploy to AWS
git clone <your-repo>
cd browser_new/cloud_deployment

# Set up NOVA_ACT_API_KEY for browser automation
export NOVA_ACT_API_KEY=your-nova-act-api-key-here

./deploy.sh
```

## 📊 Data Management

### Evidence Generation (Optional)
Generate custom claim evidence using Amazon Nova models (runs locally):

```bash
cd utils
python3.12 -m venv utils_venv
source utils_venv/bin/activate
pip install -r requirements.txt

# Example usage
python3 generate_claim_evidence.py "Wind hail damage roof damage from hailstorm call by John Smith with Policy number POL-12345 Claim number CLM-001" all --images 5 --videos 2 --transcripts 1
```

### Seeding Data
```bash
# Seed initial claims data (runs locally, connects to AWS)
cd backend
python3 seed_data.py
```

## 🐛 Troubleshooting

**DynamoDB Access Denied**: Verify ECS task role has DynamoDB permissions
**Claims Not Loading**: Check CloudWatch logs for ECS service errors
**Bedrock Analysis Fails**: Ensure region is set to `us-west-2`

### Logs
```bash
# View ECS service logs
aws logs tail /ecs/claims-app --follow
```
