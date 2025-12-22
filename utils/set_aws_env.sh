#!/bin/bash

# Set AWS credentials as environment variables
# Replace with your actual credentials
export AWS_ACCESS_KEY_ID="your_access_key_here"
export AWS_SECRET_ACCESS_KEY="your_secret_key_here"
export AWS_DEFAULT_REGION="us-east-1"

# Run the claim evidence generator
python generate_claim_evidence.py "$@"
