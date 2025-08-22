from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime, timedelta
import random

from complexity_analyzer import ComplexityAnalyzer

app = FastAPI(title="FNOL Claims Processing API")

# Initialize the complexity analyzer
complexity_analyzer = ComplexityAnalyzer()

# Sample claims data
sample_claims = [
    {
        "id": "CLM-001",
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
        "estimated_damage": 15000
    },
    {
        "id": "CLM-002",
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
            "voice_recordings": 0
        },
        "estimated_damage": 8500
    },
    {
        "id": "CLM-003",
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
        "estimated_damage": 45000
    },
    {
        "id": "CLM-004",
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
        "estimated_damage": 25000
    },
    {
        "id": "CLM-005",
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
            "voice_recordings": 0
        },
        "estimated_damage": 12000
    }
]

# In-memory storage (in production, use a database)
claims_db = {claim["id"]: claim for claim in sample_claims}

class ClaimAnalysisRequest(BaseModel):
    claim_id: str

class ClaimAnalysisResponse(BaseModel):
    claim_id: str
    complexity: str
    new_status: str
    reasoning: str

@app.get("/api/claims")
async def get_claims():
    """Get all claims that are not resolved"""
    active_claims = [claim for claim in claims_db.values() if claim["status"] != "Resolved"]
    return {"claims": active_claims}

@app.get("/api/claims/{claim_id}")
async def get_claim(claim_id: str):
    """Get a specific claim by ID"""
    if claim_id not in claims_db:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claims_db[claim_id]

@app.post("/api/analyze-claim", response_model=ClaimAnalysisResponse)
async def analyze_claim(request: ClaimAnalysisRequest):
    """Analyze claim complexity using Strands agent"""
    if request.claim_id not in claims_db:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    claim = claims_db[request.claim_id]
    
    try:
        # Use the complexity analyzer to determine if claim is complex or simple
        analysis_result = await complexity_analyzer.analyze_claim(claim)
        
        # Update claim status based on complexity
        if analysis_result["complexity"] == "Complex":
            claims_db[request.claim_id]["status"] = "Needs Review"
        else:
            claims_db[request.claim_id]["status"] = "Resolved"
        
        return ClaimAnalysisResponse(
            claim_id=request.claim_id,
            complexity=analysis_result["complexity"],
            new_status=claims_db[request.claim_id]["status"],
            reasoning=analysis_result["reasoning"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Serve React app
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
