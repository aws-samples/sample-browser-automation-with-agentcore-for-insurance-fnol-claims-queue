# Claims Evidence Generator

Generate realistic insurance claim evidence using Amazon Nova models.

## Features

- **Images**: Generate realistic damage photos using Amazon Nova Canvas
- **Videos**: Create documentation videos using Amazon Nova Reel  
- **Call Transcripts**: Generate natural-sounding phone conversations using Amazon Nova Pro
- **Audio**: Create realistic conversational audio using Amazon Nova Sonic (bidirectional streaming)

## Prerequisites

- **Python 3.12** (required for Nova Sonic bidirectional streaming SDK)
- AWS credentials configured
- Access to Amazon Bedrock Nova models
- AWS region: us-east-1 (for Nova Sonic)

## Setup

### 1. Create Python 3.12 Virtual Environment
```bash
cd utils
python3.12 -m venv utils_venv
source utils_venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Generate All Evidence Types
```bash
# Basic usage with default counts (3 images, 2 videos, 1 transcript)
python generate_claim_evidence.py "kitchen fire damage" all

# With custom counts
python generate_claim_evidence.py "Wind hail damage roof damage from hailstorm call by John Smith with Policy number POL-12345 Claim number CLM-001" all --images 5 --videos 2 --transcripts 1
```

### Generate Specific Evidence Types
```bash
# Images only
python generate_claim_evidence.py "kitchen fire damage" image --images 5

# Videos only  
python generate_claim_evidence.py "kitchen fire damage" video --videos 1

# Audio/transcripts only
python generate_claim_evidence.py "kitchen fire damage" audio --transcripts 3
```

### Real Examples
```bash
# Property damage claim
python3 generate_claim_evidence.py "Wind hail damage roof damage from hailstorm call by John Smith with Policy number POL-12345 Claim number CLM-001" all --images 5 --videos 2 --transcripts 1

# Vehicle collision
python generate_claim_evidence.py "rear-end collision for Vehicle called in by Jane Doe for policy POL-67890 Claim number CLM-002" all --images 8 --videos 1 --transcripts 0

# Kitchen fire
python3 generate_claim_evidence.py "Kitchen fire caused by electrical fault call by Bob Johnson with Policy number POL-11111 Claim number CLM-003" all --images 12 --videos 3 --transcripts 2

# Vehicle theft
python3 generate_claim_evidence.py "Vehicle stolen from parking lot call by Alice Brown with Policy number POL-22222 Claim number CLM-004" all --images 3 --videos 1 --transcripts 1

# Water damage
python3 generate_claim_evidence.py "Pipe burst in basement water damage call by Charlie Wilson with Policy number POL-33333 Claim number CLM-005" all --images 6 --videos 2 --transcripts 0
```

## Output Structure

```
generated_evidence/
├── claim_image_1_20241129_143022.png
├── claim_image_2_20241129_143025.png
├── claim_video_1_20241129_143031.mp4
├── claim_video_2_20241129_143045.mp4
├── call_transcript_1_20241129_143050.txt
├── call_transcript_2_20241129_143055.txt
├── call_conversation_1_20241129_143060.wav
├── call_conversation_2_20241129_143065.wav
└── evidence_manifest_20241129_143070.json
```

## Amazon Nova Models Used

- **Nova Canvas**: Realistic claim damage images
- **Nova Reel**: Documentation and assessment videos  
- **Nova Pro**: Natural call transcript generation
- **Nova Sonic**: Realistic conversational audio with bidirectional streaming

## Troubleshooting

**Python version error**: Ensure you're using Python 3.12 for Nova Sonic SDK compatibility
**Audio generation fails**: Check AWS credentials and us-east-1 region access
**S3 bucket errors**: Script auto-creates buckets, ensure S3 permissions
