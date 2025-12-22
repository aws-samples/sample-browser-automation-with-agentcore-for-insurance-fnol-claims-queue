from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime, timedelta
import random
import boto3
from botocore.exceptions import ClientError

from complexity_analyzer import ComplexityAnalyzer
from evidence_analyzer import EvidenceAnalyzer, tag_s3_objects

app = FastAPI(title="FNOL Claims Processing API")

# Initialize the complexity analyzer
complexity_analyzer = ComplexityAnalyzer()

# Initialize the evidence analyzer
evidence_analyzer = EvidenceAnalyzer()

# Initialize DynamoDB
def init_dynamodb():
    """Initialize DynamoDB client and table"""
    dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2'))
    table_name = os.getenv('CLAIMS_TABLE_NAME', 'Claims')
    table = dynamodb.Table(table_name)
    return table

def get_claims_from_db():
    """Get all claims from DynamoDB that are not resolved"""
    try:
        table = init_dynamodb()
        response = table.scan(
            FilterExpression="attribute_not_exists(#status) OR #status <> :resolved",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":resolved": "Resolved"}
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error getting claims: {e}")
        return []

def get_claim_from_db(claim_id: str):
    """Get a specific claim from DynamoDB"""
    try:
        table = init_dynamodb()
        response = table.get_item(Key={'claim_id': claim_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error getting claim {claim_id}: {e}")
        return None

def update_claim_status(claim_id: str, status: str):
    """Update claim status in DynamoDB"""
    try:
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression="SET #status = :status, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": status,
                ":updated_at": datetime.utcnow().isoformat() + "Z"
            }
        )
        return True
    except Exception as e:
        print(f"Error updating claim {claim_id}: {e}")
        return False

class ClaimAnalysisRequest(BaseModel):
    claim_id: str

class ClaimAnalysisResponse(BaseModel):
    claim_id: str
    complexity: str
    new_status: str
    reasoning: str

@app.on_event("startup")
async def startup_event():
    """Initialize DynamoDB connection on startup"""
    init_dynamodb()

@app.get("/api/claims")
async def get_claims():
    """Get all claims that are not resolved"""
    claims = get_claims_from_db()
    return {"claims": claims}

@app.get("/api/claims/{claim_id}")
async def get_claim(claim_id: str):
    """Get a specific claim by ID"""
    claim = get_claim_from_db(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@app.post("/api/analyze-claim", response_model=ClaimAnalysisResponse)
async def analyze_claim(request: ClaimAnalysisRequest):
    """Analyze claim complexity using Strands agent"""
    claim = get_claim_from_db(request.claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    try:
        # Use the complexity analyzer to determine if claim is complex or simple
        analysis_result = await complexity_analyzer.analyze_claim(claim)
        
        # Update claim status based on complexity
        new_status = "Needs Review" if analysis_result["complexity"] == "Complex" else "Resolved"
        
        if not update_claim_status(request.claim_id, new_status):
            raise HTTPException(status_code=500, detail="Failed to update claim status")
        
        return ClaimAnalysisResponse(
            claim_id=request.claim_id,
            complexity=analysis_result["complexity"],
            new_status=new_status,
            reasoning=analysis_result["reasoning"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/claims/{claim_id}/analyze-images")
async def analyze_images(claim_id: str):
    """Start async image analysis"""
    try:
        # Get claim data
        claim = get_claim_from_db(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Set status to processing immediately
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression='SET evidence_analysis.images = :analysis, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':analysis': {
                    'status': 'processing',
                    'started_at': datetime.now().isoformat()
                },
                ':timestamp': datetime.now().isoformat()
            }
        )
        
        # Start background processing
        import asyncio
        asyncio.create_task(process_images_async(claim_id))
        
        return {"status": "processing"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_images_async(claim_id: str):
    """Background processing for image analysis"""
    try:
        claim = get_claim_from_db(claim_id)
        image_urls = claim.get('evidence_urls', {}).get('images', [])
        
        # Analyze images
        analysis_result = await evidence_analyzer.analyze_images(claim_id, image_urls)
        
        # Update with results
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression='SET evidence_analysis.images = :analysis, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':analysis': {
                    'status': 'completed',
                    'tags': analysis_result['tags'],
                    'analysis': analysis_result['analysis'],
                    'analyzed_at': datetime.now().isoformat()
                },
                ':timestamp': datetime.now().isoformat()
            }
        )
        
        # Tag S3 objects
        if image_urls:
            await tag_s3_objects(image_urls, analysis_result['tags'])
            
    except Exception as e:
        # Update with error status
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression='SET evidence_analysis.images = :analysis, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':analysis': {
                    'status': 'error',
                    'error': str(e),
                    'analyzed_at': datetime.now().isoformat()
                },
                ':timestamp': datetime.now().isoformat()
            }
        )

@app.post("/api/claims/{claim_id}/analyze-videos")
async def analyze_videos(claim_id: str):
    """Start async video analysis"""
    try:
        # Get claim data
        claim = get_claim_from_db(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Set status to processing immediately
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression='SET evidence_analysis.videos = :analysis, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':analysis': {
                    'status': 'processing',
                    'started_at': datetime.now().isoformat()
                },
                ':timestamp': datetime.now().isoformat()
            }
        )
        
        # Start background processing
        import asyncio
        asyncio.create_task(process_videos_async(claim_id))
        
        return {"status": "processing"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_videos_async(claim_id: str):
    """Background processing for video analysis"""
    try:
        claim = get_claim_from_db(claim_id)
        video_urls = claim.get('evidence_urls', {}).get('videos', [])
        
        # Analyze videos
        analysis_result = await evidence_analyzer.analyze_videos(claim_id, video_urls)
        
        # Update with results
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression='SET evidence_analysis.videos = :analysis, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':analysis': {
                    'status': 'completed',
                    'tags': analysis_result['tags'],
                    'analysis': analysis_result['analysis'],
                    'analyzed_at': datetime.now().isoformat()
                },
                ':timestamp': datetime.now().isoformat()
            }
        )
        
        # Tag S3 objects
        if video_urls:
            await tag_s3_objects(video_urls, analysis_result['tags'])
            
    except Exception as e:
        # Update with error status
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression='SET evidence_analysis.videos = :analysis, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':analysis': {
                    'status': 'error',
                    'error': str(e),
                    'analyzed_at': datetime.now().isoformat()
                },
                ':timestamp': datetime.now().isoformat()
            }
        )

@app.post("/api/claims/{claim_id}/analyze-audio")
async def analyze_audio(claim_id: str):
    """Start async audio analysis"""
    try:
        # Get claim data
        claim = get_claim_from_db(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Set status to processing immediately
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression='SET evidence_analysis.audio = :analysis, evidence_analysis.transcripts = :analysis, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':analysis': {
                    'status': 'processing',
                    'started_at': datetime.now().isoformat()
                },
                ':timestamp': datetime.now().isoformat()
            }
        )
        
        # Start background processing
        import asyncio
        asyncio.create_task(process_audio_async(claim_id))
        
        return {"status": "processing"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_audio_async(claim_id: str):
    """Background processing for audio analysis"""
    try:
        claim = get_claim_from_db(claim_id)
        audio_urls = claim.get('evidence_urls', {}).get('audio', [])
        transcript_urls = claim.get('evidence_urls', {}).get('transcripts', [])
        
        # Analyze audio/transcripts
        analysis_result = await evidence_analyzer.analyze_audio_transcripts(claim_id, transcript_urls, audio_urls)
        
        # Update with results
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression='SET evidence_analysis.audio = :analysis, evidence_analysis.transcripts = :analysis, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':analysis': {
                    'status': 'completed',
                    'tags': analysis_result['tags'],
                    'analysis': analysis_result['analysis'],
                    'analyzed_at': datetime.now().isoformat()
                },
                ':timestamp': datetime.now().isoformat()
            }
        )
        
        # Tag S3 objects
        all_urls = audio_urls + transcript_urls
        if all_urls:
            await tag_s3_objects(all_urls, analysis_result['tags'])
            
    except Exception as e:
        # Update with error status
        table = init_dynamodb()
        table.update_item(
            Key={'claim_id': claim_id},
            UpdateExpression='SET evidence_analysis.audio = :analysis, evidence_analysis.transcripts = :analysis, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':analysis': {
                    'status': 'error',
                    'error': str(e),
                    'analyzed_at': datetime.now().isoformat()
                },
                ':timestamp': datetime.now().isoformat()
            }
        )

@app.get("/api/presigned-url")
async def get_presigned_url(s3_url: str):
    """Generate presigned URL for S3 object"""
    try:
        # Parse S3 URL
        if not s3_url.startswith('s3://'):
            raise HTTPException(status_code=400, detail="Invalid S3 URL format")
        
        parts = s3_url.replace('s3://', '').split('/', 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid S3 URL format")
        
        bucket, key = parts[0], parts[1]
        
        # Generate presigned URL
        s3_client = boto3.client('s3')
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=3600  # 1 hour
        )
        
        return {"presigned_url": presigned_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating presigned URL: {str(e)}")

# Conditionally serve React app only if build directory exists
frontend_build_path = "frontend/build"
if os.path.exists(frontend_build_path):
    app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

    @app.get("/")
    async def serve_react_app():
        return FileResponse("frontend/build/index.html")

    @app.get("/{path:path}")
    async def serve_react_app_paths(path: str):
        file_path = f"frontend/build/{path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse("frontend/build/index.html")
else:
    @app.get("/")
    async def root():
        return {"message": "Claims Processing API", "status": "running", "endpoints": ["/api/claims", "/api/analyze-claim"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
