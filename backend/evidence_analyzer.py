import os
import json
import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

import boto3
import requests
from botocore.config import Config
from strands import Agent, tool
from strands.models import BedrockModel


# ---------- S3 helpers ----------

_s3_client = boto3.client('s3', region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))


def _parse_s3_url(s3_url: str) -> tuple:
    parts = s3_url.replace('s3://', '').split('/', 1)
    return parts[0], parts[1]


def _get_presigned_url(s3_url: str) -> str:
    try:
        bucket, key = _parse_s3_url(s3_url)
        return _s3_client.generate_presigned_url(
            'get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=3600
        )
    except Exception as e:
        print(f"Error generating presigned URL for {s3_url}: {e}")
        return None


# ---------- Tools ----------

@tool(name="get_claim_evidence", description="Fetch claim evidence URLs from DynamoDB for a given claim_id. Returns the available image, video, audio, and transcript URLs.")
def get_claim_evidence(claim_id: str) -> Dict[str, Any]:
    """Fetch evidence URLs from DynamoDB so the agent knows what's available."""
    print(f"[Tool] get_claim_evidence: fetching evidence for {claim_id}")
    try:
        dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))
        table = dynamodb.Table(os.getenv('CLAIMS_TABLE_NAME', 'Claims'))
        response = table.get_item(Key={'claim_id': claim_id})

        if 'Item' not in response:
            return {"error": f"Claim {claim_id} not found"}

        claim = response['Item']
        evidence_urls = claim.get('evidence_urls', {})
        return {
            "claim_id": claim_id,
            "images": evidence_urls.get('images', []),
            "videos": evidence_urls.get('videos', []),
            "audio": evidence_urls.get('audio', []),
            "transcripts": evidence_urls.get('transcripts', []),
            "claim_type": claim.get('type', ''),
            "claim_subtype": claim.get('subtype', ''),
            "estimated_damage": claim.get('estimated_damage', 0)
        }
    except Exception as e:
        print(f"[Tool] Error fetching claim evidence: {e}")
        return {"error": str(e)}


@tool(name="examine_image", description="Download an image from S3 and analyze it for damage type, severity, affected areas, and fraud indicators using vision AI.")
def examine_image(image_s3_url: str, image_index: int, total_images: int, claim_id: str) -> Dict[str, Any]:
    """Examine a single insurance claim image via Bedrock vision."""
    print(f"[Tool] examine_image: image {image_index}/{total_images} for claim {claim_id}")

    try:
        presigned_url = _get_presigned_url(image_s3_url)
        if not presigned_url:
            return {"error": "Failed to generate presigned URL", "image_index": image_index}

        response = requests.get(presigned_url, timeout=30)
        response.raise_for_status()
        image_base64 = base64.b64encode(response.content).decode('utf-8')
        print(f"[Tool] Downloaded image {image_index}, size: {len(response.content)} bytes")
    except Exception as e:
        return {"error": f"Failed to download image: {e}", "image_index": image_index}

    analysis_prompt = (
        f"You are analyzing insurance claim image {image_index} of {total_images} for claim {claim_id}.\n"
        "Identify:\n"
        "1. Primary damage type (collision, weather_damage, vandalism, fire_damage, water_damage, theft_damage)\n"
        "2. Severity (minor, moderate, severe)\n"
        "3. Affected area (front_end, rear_end, driver_side, passenger_side, roof, interior, windshield, bumper)\n"
        "4. Characteristics (scratches, dents, cracks, breaks, burns, water_stains, missing_parts)\n"
        "5. Any fraud indicators or staging signs\n\n"
        "Return ONLY valid JSON:\n"
        '{"tags": ["tag1","tag2","tag3"], "damage_type": "...", "severity": "...", '
        '"affected_area": "...", "analysis_summary": "..."}'
    )

    try:
        config = Config(read_timeout=300, connect_timeout=60, retries={'max_attempts': 3})
        bedrock = boto3.client('bedrock-runtime', region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"), config=config)

        resp = bedrock.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.2,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": analysis_prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64}}
                    ]
                }]
            })
        )

        body = json.loads(resp['body'].read())
        text = body['content'][0]['text']
        clean = text.strip().removeprefix('```json').removesuffix('```').strip()
        result = json.loads(clean)
        result['image_index'] = image_index
        result['image_url'] = image_s3_url
        print(f"[Tool] Image {image_index} analysis: severity={result.get('severity')}, type={result.get('damage_type')}")
        return result

    except Exception as e:
        print(f"[Tool] Vision analysis failed for image {image_index}: {e}")
        return {"error": str(e), "image_index": image_index, "image_url": image_s3_url, "tags": ["analysis_error"]}


@tool(name="examine_video", description="Download a video from S3 and analyze it for damage progression, consistency, and quality using Nova 2 Lite video AI.")
def examine_video(video_s3_url: str, video_index: int, total_videos: int, claim_id: str) -> Dict[str, Any]:
    """Examine a single insurance claim video via Nova 2 Lite."""
    print(f"[Tool] examine_video: video {video_index}/{total_videos} for claim {claim_id}")

    try:
        presigned_url = _get_presigned_url(video_s3_url)
        if not presigned_url:
            return {"error": "Failed to generate presigned URL", "video_index": video_index}

        response = requests.get(presigned_url, timeout=120)
        response.raise_for_status()
        video_bytes = response.content
        print(f"[Tool] Downloaded video {video_index}, size: {len(video_bytes)} bytes")
    except Exception as e:
        return {"error": f"Failed to download video: {e}", "video_index": video_index}

    user_prompt = (
        f"Analyze this MP4 insurance claim video for claim {claim_id}. "
        f"This is video {video_index} of {total_videos}.\n\n"
        "Identify:\n"
        "1. Primary damage type (collision, weather, fire, vandalism, water)\n"
        "2. Damage severity (minor damage, moderate damage, severe damage)\n"
        "3. Video quality (poor quality, good quality, excellent quality)\n"
        "4. Consistency (consistent with scenario, questionable, suspicious)\n"
        "5. Temporal analysis (max 15 words)\n"
        "6. Analysis summary (max 30 words)\n\n"
        "Return ONLY valid JSON:\n"
        '{"damage_type":"","severity":"","video_quality":"","consistency":"","temporal_analysis":"","analysis_summary":""}'
    )

    try:
        config = Config(read_timeout=600, connect_timeout=60, retries={'max_attempts': 3})
        bedrock = boto3.client('bedrock-runtime', region_name="us-east-1", config=config)

        resp = bedrock.converse(
            modelId="global.amazon.nova-2-lite-v1:0",
            messages=[{
                "role": "user",
                "content": [
                    {"text": user_prompt},
                    {"video": {"format": "mp4", "source": {"bytes": video_bytes}}}
                ]
            }],
            additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}
        )

        text = None
        for content in resp["output"]["message"]["content"]:
            if "text" in content:
                text = content["text"]
                break

        if not text:
            return {"error": "Nova response contained no text", "video_index": video_index, "tags": ["analysis_error"]}

        clean = text.strip().removeprefix('```json').removesuffix('```').strip()
        result = json.loads(clean)

        tags = []
        for field in ['damage_type', 'severity', 'video_quality', 'consistency']:
            val = result.get(field, '')
            if val:
                tags.append(val.lower().replace(' ', '_'))
        result['tags'] = tags
        result['video_index'] = video_index
        result['video_url'] = video_s3_url
        print(f"[Tool] Video {video_index} analysis: severity={result.get('severity')}, type={result.get('damage_type')}")
        return result

    except Exception as e:
        print(f"[Tool] Nova video analysis failed for video {video_index}: {e}")
        return {"error": str(e), "video_index": video_index, "video_url": video_s3_url, "tags": ["analysis_error"]}


@tool(name="examine_transcript", description="Download a call transcript from S3 and return its content for analysis.")
def examine_transcript(transcript_s3_url: str, transcript_index: int, total_transcripts: int, claim_id: str) -> Dict[str, Any]:
    """Download and return transcript content."""
    print(f"[Tool] examine_transcript: transcript {transcript_index}/{total_transcripts} for claim {claim_id}")

    try:
        presigned_url = _get_presigned_url(transcript_s3_url)
        if not presigned_url:
            return {"error": "Failed to generate presigned URL", "transcript_index": transcript_index}

        response = requests.get(presigned_url, timeout=30)
        response.raise_for_status()
        transcript_text = response.text
        print(f"[Tool] Downloaded transcript {transcript_index}, length: {len(transcript_text)} chars")
    except Exception as e:
        return {"error": f"Failed to download transcript: {e}", "transcript_index": transcript_index}

    return {
        "transcript_index": transcript_index,
        "transcript_url": transcript_s3_url,
        "content_length": len(transcript_text),
        "transcript_content": transcript_text[:5000]
    }


@tool(name="analyze_transcript_content", description="Analyze transcript text for emotional state, story consistency, fraud risk, and credibility.")
def analyze_transcript_content(transcript_text: str, transcript_index: int, claim_id: str) -> Dict[str, Any]:
    """Use LLM to analyze transcript content."""
    print(f"[Tool] analyze_transcript_content: transcript {transcript_index} for claim {claim_id}")

    analysis_prompt = (
        f"Analyze this insurance claim call transcript for claim {claim_id}.\n\n"
        f"TRANSCRIPT:\n{transcript_text[:5000]}\n\n"
        "Identify:\n"
        "1. Emotional state (calm, distressed, angry, suspicious)\n"
        "2. Story consistency (consistent, minor_inconsistencies, major_inconsistencies)\n"
        "3. Fraud risk (none, potential, likely)\n"
        "4. Information quality (complete, partial, vague)\n"
        "5. Credibility (high, medium, low)\n\n"
        "Return ONLY valid JSON:\n"
        '{"tags":["tag1","tag2"],"emotional_state":"","story_consistency":"","fraud_risk":"","credibility":"","analysis_summary":""}'
    )

    try:
        config = Config(read_timeout=300, connect_timeout=60, retries={'max_attempts': 3})
        bedrock = boto3.client('bedrock-runtime', region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"), config=config)

        resp = bedrock.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": [{"type": "text", "text": analysis_prompt}]}]
            })
        )

        body = json.loads(resp['body'].read())
        text = body['content'][0]['text']
        clean = text.strip().removeprefix('```json').removesuffix('```').strip()
        result = json.loads(clean)
        result['transcript_index'] = transcript_index
        print(f"[Tool] Transcript {transcript_index}: fraud_risk={result.get('fraud_risk')}, credibility={result.get('credibility')}")
        return result

    except Exception as e:
        print(f"[Tool] Transcript analysis failed for {transcript_index}: {e}")
        return {"error": str(e), "transcript_index": transcript_index, "tags": ["analysis_error"]}


@tool(name="flag_evidence_gap", description="Flag a missing or insufficient piece of evidence.")
def flag_evidence_gap(gap_description: str, severity: str) -> Dict[str, Any]:
    """Record an evidence gap identified during analysis."""
    print(f"[Tool] flag_evidence_gap: {gap_description} (severity={severity})")
    return {"gap": gap_description, "severity": severity}


# ---------- Analyzer ----------

class EvidenceAnalyzer:
    def __init__(self):
        os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
        self._executor = ThreadPoolExecutor(max_workers=1)

        self.model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            temperature=0.2,
        )

        self.agent = Agent(
            name="Evidence Analyzer",
            model=self.model,
            system_prompt=(
                "You are an expert insurance evidence analyst.\n\n"
                "WORKFLOW:\n"
                "1. First call get_claim_evidence to fetch the evidence URLs from DynamoDB\n"
                "2. Based on the modality requested, examine each piece of evidence using the appropriate tool\n"
                "3. After examining all evidence, reason about patterns, gaps, and fraud indicators\n"
                "4. If you notice missing evidence, call flag_evidence_gap\n\n"
                "TOOLS:\n"
                "- get_claim_evidence: fetch evidence URLs from DynamoDB\n"
                "- examine_image: analyze an image via vision AI\n"
                "- examine_video: analyze a video via Nova 2 Lite\n"
                "- examine_transcript: download transcript content\n"
                "- analyze_transcript_content: analyze transcript for fraud/credibility\n"
                "- flag_evidence_gap: flag missing evidence\n\n"
                "FINAL ANSWER FORMAT — you MUST return valid JSON with this structure:\n"
                '{"tags": ["all_unique_tags_across_items"], "analysis_summary": "overall summary", '
                '"damage_severity": "minor|moderate|severe|unknown", '
                '"video_quality": "poor|good|excellent|unknown", '
                '"fraud_risk": "low|medium|high|unknown", '
                '"individual_results": [{"image_index|video_index|transcript_index": N, '
                '"image_url|video_url|transcript_url": "s3://...", '
                '"tags": ["this_items_specific_tags"], "damage_type": "...", "severity": "...", '
                '"fraud_risk": "...", "credibility": "...", "analysis_summary": "..."}]}\n\n'
                "CRITICAL: Each item in individual_results MUST have its own unique tags from its tool result. "
                "Do NOT copy the same tags to every item."
            ),
            tools=[get_claim_evidence, examine_image, examine_video, examine_transcript, analyze_transcript_content, flag_evidence_gap],
        )

    def _call_agent_sync(self, prompt: str):
        return self.agent(prompt)

    def _extract_text(self, result) -> str:
        if hasattr(result, 'message') and result.message:
            content = result.message.get('content', [])
            for block in content:
                if 'text' in block:
                    return block['text']
        return str(result)

    def _parse_final_json(self, text: str) -> dict:
        clean = text.strip()
        if '```json' in clean:
            parts = clean.split('```json')
            last_block = parts[-1].split('```')[0].strip()
            try:
                return json.loads(last_block)
            except json.JSONDecodeError:
                pass

        # Find largest JSON object
        best = {}
        i = 0
        while i < len(clean):
            if clean[i] == '{':
                depth = 0
                for j in range(i, len(clean)):
                    if clean[j] == '{':
                        depth += 1
                    elif clean[j] == '}':
                        depth -= 1
                        if depth == 0:
                            try:
                                candidate = json.loads(clean[i:j+1])
                                if len(clean[i:j+1]) > len(json.dumps(best)):
                                    best = candidate
                            except json.JSONDecodeError:
                                pass
                            break
            i += 1
        return best

    async def analyze(self, claim_id: str, modality: str) -> dict:
        """
        Single entry point. The agent fetches evidence from DynamoDB and decides what to analyze.
        
        Args:
            claim_id: The claim to analyze
            modality: "images", "videos", or "audio" — which button was clicked
            
        Returns:
            Dict with 'tags', 'analysis', 'individual_analyses' matching UI contract.
        """
        print(f"\n=== EVIDENCE AGENT: {modality.upper()} ANALYSIS FOR CLAIM {claim_id} ===")

        prompt = (
            f"Analyze the {modality.upper()} evidence for insurance claim {claim_id}.\n\n"
            f"Steps:\n"
            f"1. Call get_claim_evidence with claim_id=\"{claim_id}\" to fetch available evidence URLs\n"
            f"2. From the result, look at the '{modality}' "
        )

        if modality == "audio":
            prompt += (
                "and 'transcripts' URLs\n"
                "3. For each transcript: call examine_transcript, then analyze_transcript_content with the text\n"
            )
        elif modality == "images":
            prompt += (
                "URLs\n"
                "3. For each image: call examine_image\n"
            )
        elif modality == "videos":
            prompt += (
                "URLs\n"
                "3. For each video: call examine_video\n"
            )

        prompt += (
            "4. After examining all items, flag any evidence gaps\n"
            "5. Provide your FINAL ANSWER JSON with individual_results containing per-item tags\n\n"
            f"Use claim_id=\"{claim_id}\" in all tool calls."
        )

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(self._executor, self._call_agent_sync, prompt)
            response_text = self._extract_text(result)
            print(f"Agent response length: {len(response_text)} chars")

            final = self._parse_final_json(response_text)
            tags = final.get('tags', [])
            summary = final.get('analysis_summary', f'Analyzed {modality}')

            # Build individual_analyses in the format UI expects
            individual_analyses = []
            for item in final.get('individual_results', []):
                if modality == "images":
                    individual_analyses.append({
                        'image_index': item.get('image_index', 0),
                        'image_url': item.get('image_url', ''),
                        'analysis': {
                            'tags': item.get('tags', []),
                            'damage_type': item.get('damage_type', ''),
                            'severity': item.get('severity', ''),
                            'analysis_summary': item.get('analysis_summary', '')
                        }
                    })
                elif modality == "videos":
                    individual_analyses.append({
                        'video_index': item.get('video_index', 0),
                        'video_url': item.get('video_url', ''),
                        'analysis': {
                            'tags': item.get('tags', []),
                            'damage_type': item.get('damage_type', ''),
                            'severity': item.get('severity', ''),
                            'analysis_summary': item.get('analysis_summary', '')
                        }
                    })
                elif modality == "audio":
                    individual_analyses.append({
                        'transcript_index': item.get('transcript_index', 0),
                        'transcript_url': item.get('transcript_url', ''),
                        'analysis': {
                            'tags': item.get('tags', []),
                            'fraud_risk': item.get('fraud_risk', ''),
                            'credibility': item.get('credibility', ''),
                            'analysis_summary': item.get('analysis_summary', '')
                        }
                    })

            # Fallback if agent didn't produce individual_results
            if not individual_analyses:
                individual_analyses.append({
                    'image_index' if modality == 'images' else 'video_index' if modality == 'videos' else 'transcript_index': 1,
                    'analysis': {'tags': tags}
                })

            return {
                'tags': tags,
                'analysis': {'analysis_summary': summary},
                'individual_analyses': individual_analyses,
                'damage_severity': final.get('damage_severity', 'unknown'),
                'video_quality': final.get('video_quality', 'unknown'),
                'fraud_risk': final.get('fraud_risk', 'unknown'),
            }

        except Exception as e:
            print(f"ERROR in evidence agent ({modality}) for {claim_id}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'tags': ['analysis_error'],
                'analysis': {'analysis_summary': f'Error: {e}'},
                'individual_analyses': [],
                'damage_severity': 'unknown',
                'video_quality': 'unknown',
                'fraud_risk': 'unknown',
            }


# ---------- S3 tagging ----------

async def tag_s3_objects_individual(individual_analyses: list, url_key: str):
    """Tag each S3 object with its individual analysis results."""
    s3 = boto3.client('s3')

    for analysis in individual_analyses:
        try:
            file_url = analysis[url_key]
            file_tags = analysis.get('analysis', {}).get('tags', [])
            file_index = analysis.get('image_index', analysis.get('video_index', analysis.get('transcript_index', 1)))

            bucket, key = _parse_s3_url(file_url)

            tag_set = [
                {'Key': 'analysis_status', 'Value': 'completed'},
                {'Key': 'file_index', 'Value': str(file_index)}
            ]
            for i, tag in enumerate(file_tags[:8]):
                tag_set.append({'Key': f'tag_{i}', 'Value': tag})

            s3.put_object_tagging(Bucket=bucket, Key=key, Tagging={'TagSet': tag_set})
        except Exception as e:
            print(f"Error tagging S3 object {analysis.get(url_key, 'unknown')}: {e}")
