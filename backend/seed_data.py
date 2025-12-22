#!/usr/bin/env python3
"""
Idempotent script to seed DynamoDB with sample claims data and enhance with evidence URLs
"""
import boto3
import os
import json
from pathlib import Path
from datetime import datetime
import sys

# Sample claims data
sample_claims = [
    {
        "claim_id": "CLM-001",
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
    },
    {
        "claim_id": "CLM-002",
        "type": "Vehicle",
        "subtype": "Collision",
        "date_of_loss": "2024-01-20",
        "description": "Rear-end collision on highway",
        "status": "New",
        "policy_holder": "Jane Doe",
        "policy_number": "POL-67890",
        "evidence": {
            "images": 8,
            "videos": 1,
            "voice_recordings": 1
        },
        "estimated_damage": 8500,
        "created_at": "2024-01-20T14:30:00Z",
        "updated_at": "2024-01-20T14:30:00Z"
    },
    {
        "claim_id": "CLM-003",
        "type": "Property",
        "subtype": "Fire Damage",
        "date_of_loss": "2024-01-25",
        "description": "Kitchen fire caused by electrical fault",
        "status": "New",
        "policy_holder": "Bob Johnson",
        "policy_number": "POL-11111",
        "evidence": {
            "images": 12,
            "videos": 3,
            "voice_recordings": 2
        },
        "estimated_damage": 45000,
        "created_at": "2024-01-25T09:15:00Z",
        "updated_at": "2024-01-25T09:15:00Z"
    },
    {
        "claim_id": "CLM-004",
        "type": "Vehicle",
        "subtype": "Theft",
        "date_of_loss": "2024-02-01",
        "description": "Vehicle stolen from parking lot",
        "status": "New",
        "policy_holder": "Alice Brown",
        "policy_number": "POL-22222",
        "evidence": {
            "images": 3,
            "videos": 1,
            "voice_recordings": 1
        },
        "estimated_damage": 25000,
        "created_at": "2024-02-01T16:45:00Z",
        "updated_at": "2024-02-01T16:45:00Z"
    },
    {
        "claim_id": "CLM-005",
        "type": "Property",
        "subtype": "Water Damage",
        "date_of_loss": "2024-02-05",
        "description": "Pipe burst in basement",
        "status": "New",
        "policy_holder": "Charlie Wilson",
        "policy_number": "POL-33333",
        "evidence": {
            "images": 6,
            "videos": 2,
            "voice_recordings": 1
        },
        "estimated_damage": 12000,
        "created_at": "2024-02-05T11:20:00Z",
        "updated_at": "2024-02-05T11:20:00Z"
    }
]

def upload_evidence_for_claim(s3_client, bucket_name, claim_id, evidence_dir):
    """Upload evidence files for a specific claim and return S3 URLs"""
    evidence_urls = {'images': [], 'videos': [], 'audio': [], 'transcripts': []}
    
    # Look for manifest file for this claim (try both naming conventions)
    manifest_file = evidence_dir / f"{claim_id.replace('-', '_')}_manifest.json"
    if not manifest_file.exists():
        manifest_file = evidence_dir / f"{claim_id}_manifest.json"
    
    if not manifest_file.exists():
        print(f"  No evidence manifest found for {claim_id}")
        return evidence_urls
    
    try:
        with open(manifest_file) as f:
            manifest = json.load(f)
        
        print(f"  Processing evidence manifest for {claim_id}")
        
        # Upload images
        if 'images' in manifest['evidence']:
            for image_path in manifest['evidence']['images']:
                # Handle relative paths in manifest
                if not os.path.isabs(image_path):
                    full_path = evidence_dir.parent / image_path
                else:
                    full_path = Path(image_path)
                
                if full_path.exists():
                    s3_key = f"{claim_id}/images/{full_path.name}"
                    s3_client.upload_file(str(full_path), bucket_name, s3_key)
                    evidence_urls['images'].append(f"s3://{bucket_name}/{s3_key}")
        
        # Upload videos
        if 'videos' in manifest['evidence']:
            for video_path in manifest['evidence']['videos']:
                # Handle relative paths in manifest
                if not os.path.isabs(video_path):
                    full_path = evidence_dir.parent / video_path
                else:
                    full_path = Path(video_path)
                
                if full_path.exists():
                    s3_key = f"{claim_id}/videos/{full_path.name}"
                    s3_client.upload_file(str(full_path), bucket_name, s3_key)
                    evidence_urls['videos'].append(f"s3://{bucket_name}/{s3_key}")
        
        # Upload transcripts and audio
        if 'call_transcripts' in manifest['evidence']:
            for transcript_path in manifest['evidence']['call_transcripts']:
                # Handle relative paths in manifest
                if not os.path.isabs(transcript_path):
                    full_path = evidence_dir.parent / transcript_path
                else:
                    full_path = Path(transcript_path)
                
                if full_path.exists():
                    # Upload transcript
                    s3_key = f"{claim_id}/transcripts/{full_path.name}"
                    s3_client.upload_file(str(full_path), bucket_name, s3_key)
                    evidence_urls['transcripts'].append(f"s3://{bucket_name}/{s3_key}")
                    
                    # Upload corresponding audio file
                    audio_file = str(full_path).replace('_transcript_', '_audio_').replace('.txt', '.wav')
                    if os.path.exists(audio_file):
                        s3_key = f"{claim_id}/audio/{Path(audio_file).name}"
                        s3_client.upload_file(audio_file, bucket_name, s3_key)
                        evidence_urls['audio'].append(f"s3://{bucket_name}/{s3_key}")
        
        print(f"  ✓ Uploaded evidence: {len(evidence_urls['images'])} images, {len(evidence_urls['videos'])} videos, {len(evidence_urls['audio'])} audio, {len(evidence_urls['transcripts'])} transcripts")
        
    except Exception as e:
        print(f"  Error processing evidence for {claim_id}: {e}")
    
    return evidence_urls

def enhance_claims_with_evidence(table, force_update=False):
    """Enhance existing claims with evidence URLs and analysis structure"""
    
    # Check if evidence bucket exists
    bucket_name = os.getenv('EVIDENCE_BUCKET_NAME')
    if not bucket_name:
        print("EVIDENCE_BUCKET_NAME not set, skipping evidence enhancement")
        return True
    
    # Check if evidence directory exists
    evidence_dir = Path('../utils/generated_evidence')
    if not evidence_dir.exists():
        print(f"Evidence directory not found: {evidence_dir}")
        print("Skipping evidence enhancement")
        return True
    
    try:
        s3_client = boto3.client('s3')
        # Test bucket access
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✓ Evidence bucket accessible: {bucket_name}")
    except Exception as e:
        print(f"Cannot access evidence bucket {bucket_name}: {e}")
        print("Skipping evidence enhancement")
        return True
    
    print("Enhancing claims with evidence data...")
    
    # Get all existing claims
    response = table.scan()
    claims = response['Items']
    
    enhanced_count = 0
    
    for claim in claims:
        claim_id = claim['claim_id']
        
        # Always update evidence data (removed skip condition)
        if 'evidence_urls' in claim:
            print(f"  {claim_id}: Updating existing evidence data...")
        else:
            print(f"  {claim_id}: Adding evidence data...")
        
        # Upload evidence and get URLs
        evidence_urls = upload_evidence_for_claim(s3_client, bucket_name, claim_id, evidence_dir)
        
        # Create evidence analysis structure
        evidence_analysis = {
            'images': {'status': 'pending', 'tags': [], 'analysis': {}, 'analyzed_at': None},
            'videos': {'status': 'pending', 'tags': [], 'analysis': {}, 'analyzed_at': None},
            'audio': {'status': 'pending', 'tags': [], 'analysis': {}, 'analyzed_at': None},
            'transcripts': {'status': 'pending', 'tags': [], 'analysis': {}, 'analyzed_at': None}
        }
        
        # Update claim with evidence data
        update_expression = 'SET evidence_urls = :urls, evidence_analysis = :analysis, updated_at = :timestamp'
        expression_values = {
            ':urls': evidence_urls,
            ':analysis': evidence_analysis,
            ':timestamp': datetime.now().isoformat()
        }
        
        # Add analysis_status for GSI if evidence exists
        if any(evidence_urls.values()):
            update_expression += ', analysis_status = :status'
            expression_values[':status'] = 'pending'
        
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        enhanced_count += 1
        print(f"  ✓ {claim_id}: Enhanced with evidence data")
    
    print(f"Enhanced {enhanced_count} claims with evidence data")
    return True

def seed_dynamodb(force_update=False):
    """Idempotent seeding: Insert new claims and enhance existing ones with evidence"""
    try:
        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2'))
        table_name = os.getenv('CLAIMS_TABLE_NAME', 'Claims')
        table = dynamodb.Table(table_name)
        
        print(f"Processing table: {table_name}")
        
        # Get existing claims
        response = table.scan()
        existing_claims = {item['claim_id']: item for item in response['Items']}
        
        # Insert new claims that don't exist
        new_claims_added = 0
        for claim in sample_claims:
            if claim['claim_id'] not in existing_claims:
                table.put_item(Item=claim)
                print(f"✓ Inserted new claim: {claim['claim_id']}")
                new_claims_added += 1
            else:
                print(f"  {claim['claim_id']}: Already exists, skipping insert")
        
        if new_claims_added > 0:
            print(f"Added {new_claims_added} new claims")
        else:
            print("No new claims to add")
        
        # Enhance all claims with evidence (always update for fresh data)
        enhance_claims_with_evidence(table, force_update=True)
        
        print("✓ Seeding and enhancement completed successfully")
        
    except Exception as e:
        print(f"Error in seeding process: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import sys
    
    force_update = False
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        force_update = True
        print("Force mode: Will update existing evidence data")
    
    success = seed_dynamodb(force_update)
    sys.exit(0 if success else 1)
