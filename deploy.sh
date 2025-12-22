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
echo "  - DynamoDB Table: Claims"
echo "  - S3 Evidence Bucket: claims-evidence-$CDK_DEFAULT_ACCOUNT-$CDK_DEFAULT_REGION"
echo "  - ECS Fargate Service with containerized app"
echo "  - Application Load Balancer"
echo "  - CloudFront Distribution"
echo ""
echo "🔗 Access your application via the CloudFront URL shown above"
echo ""
echo "⚠️  NEXT STEPS - Seed the database with evidence:"
echo "   1. Wait 2-3 minutes for ECS service to be healthy"
echo "   2. Run the following commands:"
echo ""
echo "   cd ../backend"
echo "   export CLAIMS_TABLE_NAME="Claims"
echo "   export EVIDENCE_BUCKET_NAME="claims-evidence-$CDK_DEFAULT_ACCOUNT-$CDK_DEFAULT_REGION"
echo "   python3 seed_data.py"
echo ""
echo "   This will add evidence URLs and analysis structure to all claims."
