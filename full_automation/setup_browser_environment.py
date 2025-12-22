#!/usr/bin/env python3
"""
Fully automated setup script for AgentCore recording-enabled browser.

It performs ALL required tasks:

  1. Create S3 bucket for session recordings (if missing)
  2. Create IAM role for AgentCore browser (if missing)
  3. Automatically validates + patches IAM trust policy
     => ensures both principals: bedrock-agentcore + bedrock
  4. Attach S3 permissions + CloudWatch logging
  5. Create recording-enabled AgentCore browser
  6. Save browserIdentifier into browser_id.txt

After running this script successfully,
run your automation using run_claims_automation.py.
"""

import boto3
import botocore
import json
import uuid
import os

REGION = "us-west-2"
BUCKET_NAME = "agentcore-browser-recordings-piyali"
PREFIX = "browser-recordings"
ROLE_NAME = "AgentCoreBrowserRecordingRole"
BROWSER_NAME = "ClaimsRecordingBrowser"
OUTPUT_BROWSER_FILE = "browser_id.txt"

s3 = boto3.client("s3", region_name=REGION)
iam = boto3.client("iam")
agentcore = boto3.client("bedrock-agentcore-control", region_name=REGION)
sts = boto3.client("sts")
ACCOUNT_ID = sts.get_caller_identity()["Account"]


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def bucket_exists(name):
    try:
        s3.head_bucket(Bucket=name)
        return True
    except botocore.exceptions.ClientError:
        return False


def create_bucket():
    if bucket_exists(BUCKET_NAME):
        print(f"✔ S3 bucket already exists: {BUCKET_NAME}")
        return

    print(f"⏳ Creating S3 bucket: {BUCKET_NAME}")
    s3.create_bucket(
        Bucket=BUCKET_NAME,
        CreateBucketConfiguration={"LocationConstraint": REGION}
    )
    print(f"✔ Created bucket: {BUCKET_NAME}")


def ensure_trust_policy(role_name):
    """
    Ensure the IAM role trust policy includes BOTH required principals:
      - bedrock-agentcore.amazonaws.com
      - bedrock.amazonaws.com
    """
    print("⏳ Validating trust policy...")

    trust_needed = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "bedrock-agentcore.amazonaws.com",
                    "bedrock.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }]
    }

    try:
        current = iam.get_role(RoleName=role_name)["Role"]["AssumeRolePolicyDocument"]

        # normalize principal to list
        principals = current.get("Statement", [])[0].get("Principal", {}).get("Service", [])
        if isinstance(principals, str):
            principals = [principals]

        missing = []
        for svc in ["bedrock-agentcore.amazonaws.com", "bedrock.amazonaws.com"]:
            if svc not in principals:
                missing.append(svc)

        if not missing:
            print("✔ Trust policy already correct.")
            return

        print(f"⚠ Trust policy missing principals: {missing}")
        print("⏳ Patching trust policy...")

        iam.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=json.dumps(trust_needed)
        )
        print("✔ Trust policy patched successfully.")

    except iam.exceptions.NoSuchEntityException:
        print(f"❌ Role {role_name} does not exist.")
        raise


def create_iam_role():
    """
    Creates IAM role OR fixes it if already exists.
    """
    role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}"

    try:
        iam.get_role(RoleName=ROLE_NAME)
        print(f"✔ IAM role already exists: {ROLE_NAME}")

        # auto-patch trust policy (fixing your previous error)
        ensure_trust_policy(ROLE_NAME)
        return role_arn

    except iam.exceptions.NoSuchEntityException:
        print(f"⏳ Creating IAM role: {ROLE_NAME}")

        assume_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "bedrock-agentcore.amazonaws.com",
                        "bedrock.amazonaws.com"
                    ]
                },
                "Action": "sts:AssumeRole"
            }]
        }

        iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(assume_policy)
        )

        print("✔ IAM role created.")

        # Apply S3 permissions
        s3_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{BUCKET_NAME}",
                    f"arn:aws:s3:::{BUCKET_NAME}/*"
                ]
            }]
        }

        iam.put_role_policy(
            RoleName=ROLE_NAME,
            PolicyName="BrowserRecordingS3Access",
            PolicyDocument=json.dumps(s3_policy)
        )

        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
        )

        print("✔ Attached S3 + CloudWatch permissions.")

        return role_arn


def create_browser(role_arn):
    """
    Creates the recording-enabled browser if missing.
    Otherwise returns the existing browser.
    """
    print(f"⏳ Checking existing browsers...")

    browsers = agentcore.list_browsers().get("browsers", [])
    for browser in browsers:
        if browser["name"] == BROWSER_NAME:
            print(f"✔ Browser already exists: {browser['browserIdentifier']}")
            return browser["browserIdentifier"]

    print(f"⏳ Creating recording-enabled browser tool: {BROWSER_NAME}")

    response = agentcore.create_browser(
        name=BROWSER_NAME,
        description="Recording-enabled browser for cloud claims automation",
        networkConfiguration={"networkMode": "PUBLIC"},
        executionRoleArn=role_arn,
        clientToken=str(uuid.uuid4()),
        recording={
            "enabled": True,
            "s3Location": {
                "bucket": BUCKET_NAME,
                "prefix": PREFIX
            }
        }
    )

    browser_id = response.get("browserId") or response.get("browserIdentifier")
    print(f"✔ Browser created: {browser_id}")
    return browser_id


def save_browser_id(browser_id):
    with open(OUTPUT_BROWSER_FILE, "w") as f:
        f.write(browser_id)
    print(f"✔ Saved browser ID to {OUTPUT_BROWSER_FILE}")


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

def main():
    print("\n=== AGENTCORE BROWSER SETUP START ===\n")

    create_bucket()
    role_arn = create_iam_role()
    ensure_trust_policy(ROLE_NAME)   # always enforced
    browser_id = create_browser(role_arn)

    save_browser_id(browser_id)

    print("\n=== SETUP COMPLETE ===")
    print(f"Browser ID: {browser_id}")
    print("You can now run: python run_claims_automation.py")
    print("Recordings → S3")
    print("Live View → AWS Console → AgentCore → Browsers → Sessions")
    print("browser_id.txt updated\n")


if __name__ == "__main__":
    main()
