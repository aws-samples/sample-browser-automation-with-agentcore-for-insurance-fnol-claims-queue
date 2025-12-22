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
python generate_claim_evidence.py "kitchen fire damage" all
```

### Generate Specific Evidence Types
```bash
# Images only
python generate_claim_evidence.py "kitchen fire damage" image

# Videos only  
python generate_claim_evidence.py "kitchen fire damage" video

# Audio/transcripts only
python generate_claim_evidence.py "kitchen fire damage" audio
```

### Custom Counts
```bash
python generate_claim_evidence.py "kitchen fire damage" image --images 5
python generate_claim_evidence.py "kitchen fire damage" video --videos 1
python generate_claim_evidence.py "kitchen fire damage" audio --transcripts 3
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
