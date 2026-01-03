#!/bin/bash

# Claims Processing Deployment Script

set -e

echo "🚀 Starting Claims Processing Deployment..."

# Set AWS environment variables for CDK
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-west-2
export AWS_DEFAULT_REGION=us-west-2

echo "📋 Using AWS Account: $CDK_DEFAULT_ACCOUNT"
echo "📋 Using AWS Region: $CDK_DEFAULT_REGION"

# Change to CDK directory
cd cdk

# Install CDK dependencies
echo "📦 Installing CDK dependencies..."
npm install

# Bootstrap CDK if needed
echo "🔧 Bootstrapping CDK..."
cdk bootstrap aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION

# Deploy the stack (this builds the Docker container and deploys everything)
echo "🏗️ Deploying CDK stack..."
cdk deploy --all --require-approval never

echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Resources created:"
echo "  - DynamoDB Table: ClaimsEvidence"
echo "  - S3 Evidence Bucket: claims-evidencestore-$CDK_DEFAULT_ACCOUNT-$CDK_DEFAULT_REGION"
echo "  - ECS Fargate Service with containerized app"
echo "  - Application Load Balancer"
echo "  - CloudFront Distribution. Make note of the cloudfront url."
echo ""
echo "🔗 Access your application via the CloudFront URL shown above"
echo ""
echo "⚠️  NEXT STEPS:"
echo "   1. Wait 2-3 minutes for ECS service to be healthy"
echo ""
echo "   2. Generate evidence (optional - skip if using existing evidence):"
echo "   cd utils"
echo "   python3.12 -m venv utils_venv"
echo "   source utils_venv/bin/activate"
echo "   pip install -r requirements.txt"
echo "   # Run evidence generation commands as needed, e.g.:"
echo "   # python3 generate_claim_evidence.py \"Wind hail damage...\" all --images 5 --videos 2 --transcripts 1"
echo ""
echo "   3. Seed the database:"
echo "   cd backend   "
echo "   export CLAIMS_TABLE_NAME="ClaimsEvidence"     "
echo "   export EVIDENCE_BUCKET_NAME="claims-evidencestore-$CDK_DEFAULT_ACCOUNT-$CDK_DEFAULT_REGION" "
echo "   python3 seed_data.py "
echo ""
echo "   4. Set up browser automation (optional):"
echo "   cd ../full_automation"
echo "   python3.12 -m venv automation_venv"
echo "   source automation_venv/bin/activate"
echo "   pip install -r requirements.txt"
echo "   export NOVA_ACT_API_KEY=your-nova-act-api-key-here"
echo "   export CLOUDFRONT_URL=<value of cloudfront url when the cdk was deployed> "
echo "   python3 setup_browser_environment.py"
echo "   python3 run_claims_automation_fixed.py"
echo ""
echo "   This will add evidence URLs and analysis structure to all claims."
