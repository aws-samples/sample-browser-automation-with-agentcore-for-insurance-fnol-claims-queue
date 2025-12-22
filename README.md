# Claims Processing Cloud Deployment

A cloud-native insurance claims processing system using AWS services with DynamoDB for persistent data storage.

## 🏗️ Architecture

- **Frontend**: React application served via CloudFront
- **Backend**: FastAPI on ECS Fargate with DynamoDB integration
- **Database**: DynamoDB for claims data persistence
- **AI/ML**: Amazon Bedrock with Strands agents for complexity analysis
- **Security**: WAF protection and CloudFront-only ALB access

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Node.js and npm
- Python 3.12
- Docker (for local testing)
- CDK CLI: `npm install -g aws-cdk`

## 🚀 Quick Deployment

### Option 1: Automated Deployment
```bash
# Clone and deploy everything
git clone <your-repo>
cd browser_new/cloud_deployment
./deploy.sh
```

### Option 2: Manual Deployment
```bash
# 1. Deploy infrastructure
cd cdk
npm install
npx cdk deploy

# 2. Seed DynamoDB data
cd ../backend
export AWS_DEFAULT_REGION=us-west-2
export CLAIMS_TABLE_NAME=Claims
python3 seed_data.py
```

## 🗄️ Database Schema

### DynamoDB Table: Claims
```json
{
  "claim_id": "CLM-001",           // Primary Key
  "type": "Property",
  "subtype": "Wind/Hail Damage",
  "date_of_loss": "2024-01-15",
  "description": "Roof damage from hailstorm",
  "status": "New",
  "policy_holder": "John Smith",
  "policy_number": "POL-12345",
  "evidence": {
    "images": 5,
    "videos": 2,
    "voice_recordings": 1
  },
  "estimated_damage": 15000,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

## 🔧 API Endpoints

- `GET /api/claims` - Get all active claims from DynamoDB
- `GET /api/claims/{claim_id}` - Get specific claim
- `POST /api/analyze-claim` - Analyze claim complexity and update status

## 🧪 Testing

### Local Testing with DynamoDB
```bash
# Start DynamoDB Local (optional)
docker run -p 8000:8000 amazon/dynamodb-local

# Set environment variables
export AWS_DEFAULT_REGION=us-west-2
export CLAIMS_TABLE_NAME=Claims

# Run backend
cd backend
python3 main.py
```

### Frontend Testing
```bash
cd frontend
npm install
npm start
```

## 🔐 Security & Permissions

### ECS Task Role Permissions
- `dynamodb:GetItem`
- `dynamodb:PutItem` 
- `dynamodb:UpdateItem`
- `dynamodb:Scan`
- `dynamodb:Query`
- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`

### Network Security
- ALB accepts traffic only from CloudFront prefix list
- ECS tasks in public subnets with security groups
- WAF protection on CloudFront distribution

## 📊 Data Management

### Seeding Data
```bash
# Seed initial claims data
cd backend
python3 seed_data.py

# Force overwrite existing data
python3 seed_data.py --force
```

### Backup & Recovery
DynamoDB provides:
- Point-in-time recovery
- On-demand backups
- Cross-region replication (if configured)

## 🐛 Troubleshooting

### Common Issues

**DynamoDB Access Denied**
- Verify ECS task role has DynamoDB permissions
- Check table name environment variable: `CLAIMS_TABLE_NAME`

**Claims Not Loading**
- Verify DynamoDB table exists and has data
- Check CloudWatch logs for ECS service errors

**Bedrock Analysis Fails**
- Ensure region is set to `us-west-2`
- Verify Bedrock model access permissions

### Logs & Monitoring
```bash
# View ECS service logs
aws logs tail /ecs/claims-app --follow

# Check DynamoDB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=Claims
```

## 💰 Cost Optimization

- **DynamoDB**: Pay-per-request billing mode
- **ECS**: Single Fargate task (scale as needed)
- **CloudFront**: Free tier covers most development usage
- **Bedrock**: Pay-per-API-call pricing

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
- name: Deploy Claims Processing
  run: |
    cd cloud_deployment
    ./deploy.sh
  env:
    AWS_DEFAULT_REGION: us-west-2
```

## 📈 Scaling Considerations

- **DynamoDB**: Auto-scales with pay-per-request
- **ECS**: Configure auto-scaling based on CPU/memory
- **CloudFront**: Global edge locations handle traffic spikes
- **Bedrock**: Managed service with built-in scaling

---

### Development vs Production

**Development**:
- Single ECS task
- DynamoDB with removal policy DESTROY
- Basic monitoring

**Production**:
- Multi-AZ ECS deployment
- DynamoDB with backup enabled
- Enhanced monitoring and alerting
- Custom domain with SSL certificate
