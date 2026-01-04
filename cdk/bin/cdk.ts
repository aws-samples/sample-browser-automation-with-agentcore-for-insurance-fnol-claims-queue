#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ClaimsProcessingStack } from '../lib/claims-processing-stack';
import { WAFStack } from '../lib/waf-stack';

const app = new cdk.App();

// WAF Stack in us-east-1 (required for CloudFront)
const wafStack = new WAFStack(app, 'ClaimsFNOLWAFStack', {
  crossRegionReferences: true,
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: 'us-east-1'
  }
});

// Main stack in your preferred region
new ClaimsProcessingStack(app, 'ClaimsFNOLProcessingStack', {
  wafStack: wafStack,
  crossRegionReferences: true,
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION 
  }
});

app.synth();
