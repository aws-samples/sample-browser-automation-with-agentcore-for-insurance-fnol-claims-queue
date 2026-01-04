import boto3
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import base64
import requests

from strands import Agent
from strands.models import BedrockModel

class EvidenceAnalyzer:
    def __init__(self):
        # Ensure Bedrock region (override from env if you prefer)
        os.environ.setdefault("AWS_DEFAULT_REGION", "us-west-2")
        
        self._executor = ThreadPoolExecutor(max_workers=1)
        
        # Build a Bedrock model object for Strands
        self.model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-west-2"),
            temperature=0.2,
        )
        
        self.agent = Agent(
            name="Evidence Analyzer",
            model=self.model,
            system_prompt=(
                "You are an expert insurance evidence analyzer. Analyze evidence and return JSON with:\n"
                "- tags: array of 3-5 specific descriptive tags from this list:\n"
                "  Images: severe, moderate, minor, high_damage, multiple_areas, front_impact, side_impact, rear_impact, vehicle_damage, property_damage, fraud_indicators, collision, weather, vandalism\n"
                "  Videos: progressive_damage, timeline_accurate, scene_walkthrough, damage_consistent\n"
                "  Audio: emotional_distress, inconsistent_story, caller_credible, caller_suspicious, fraud_indicators\n"
                "- analysis_summary: brief summary\n"
                "- severity/quality/risk: appropriate rating\n\n"
                "ALWAYS return valid JSON. Use only tags from the specified lists above."
            )
        )
        
        self.s3 = boto3.client('s3')
    
    def _get_presigned_url(self, s3_url: str) -> str:
        """Generate presigned URL for S3 object"""
        try:
            bucket, key = self._parse_s3_url(s3_url)
            presigned_url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=3600
            )
            return presigned_url
        except Exception as e:
            print(f"Error generating presigned URL for {s3_url}: {e}")
            return None
    
    def _download_and_encode_image(self, s3_url: str) -> str:
        """Download image from S3 and encode as base64"""
        try:
            presigned_url = self._get_presigned_url(s3_url)
            if not presigned_url:
                return None
            
            print(f"Downloading image from: {presigned_url}")
            response = requests.get(presigned_url, timeout=30)
            response.raise_for_status()
            
            # Encode image as base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            print(f"Successfully downloaded and encoded image, size: {len(image_base64)} chars")
            return image_base64
            
        except Exception as e:
            print(f"Error downloading image from {s3_url}: {e}")
            return None
    
    def _parse_s3_url(self, s3_url: str) -> tuple:
        """Parse S3 URL to bucket and key"""
        parts = s3_url.replace('s3://', '').split('/', 1)
        return parts[0], parts[1]
        """Parse S3 URL to bucket and key"""
        parts = s3_url.replace('s3://', '').split('/', 1)
        return parts[0], parts[1]
    
    def _call_agent_sync(self, prompt: str) -> str:
        """Synchronous wrapper for agent call"""
        result = self.agent(prompt)
        
        # Extract text from Strands Agent result structure
        if hasattr(result, 'message') and result.message:
            content = result.message.get('content', [])
            if content and len(content) > 0:
                return content[0].get('text', '')
        
        # Fallback to string conversion
        return str(result)
    
    async def analyze_images(self, claim_id: str, image_urls: list) -> dict:
        """Analyze claim images individually and return comprehensive tags and analysis"""
        
        print(f"\n=== STARTING IMAGE ANALYSIS FOR CLAIM {claim_id} ===")
        print(f"Total images to analyze: {len(image_urls)}")
        
        if not image_urls:
            print("No images to analyze")
            return {
                'tags': [],
                'analysis': {'analysis_summary': 'No images to analyze'},
                'damage_severity': 'unknown'
            }
        
        all_tags = []
        individual_analyses = []
        
        try:
            # Analyze each image individually
            for i, image_url in enumerate(image_urls):
                print(f"\n--- Analyzing Image {i+1}/{len(image_urls)} ---")
                print(f"Image URL: {image_url}")
                
                # Download and encode the image
                image_base64 = self._download_and_encode_image(image_url)
                if not image_base64:
                    print(f"Failed to download image {i+1}, skipping...")
                    individual_analyses.append({
                        'image_index': i+1,
                        'image_url': image_url,
                        'analysis': {'error': 'Failed to download image'}
                    })
                    continue
                
                # Create vision analysis prompt with image
                analysis_prompt = f"""
                You are analyzing an insurance claim image for claim {claim_id}.
                
                This is image {i+1} of {len(image_urls)} total images.
                
                Please examine this image carefully and identify:
                1. Primary damage type (collision, weather, vandalism, fire, water, etc.)
                2. Damage severity (minor, moderate, severe)
                3. Affected vehicle/property areas (front, rear, side, roof, interior, etc.)
                4. Specific damage characteristics (scratches, dents, cracks, breaks, etc.)
                5. Any fraud indicators or inconsistencies
                
                Return ONLY valid JSON with these exact fields:
                {{
                    "tags": ["damage_type", "severity_level", "affected_area", "damage_characteristic"],
                    "damage_type": "specific damage type found",
                    "severity": "minor/moderate/severe", 
                    "affected_area": "specific area damaged",
                    "damage_characteristic": "specific characteristic observed",
                    "analysis_summary": "Brief description of what you see in this image"
                }}
                
                Use specific tags from these lists:
                Damage types: collision, weather_damage, vandalism, fire_damage, water_damage, theft_damage
                Severity: minor, moderate, severe
                Areas: front_end, rear_end, driver_side, passenger_side, roof, interior, windshield, bumper
                Characteristics: scratches, dents, cracks, breaks, burns, water_stains, missing_parts
                """
                
                # Use Bedrock directly for vision analysis
                try:
                    import boto3
                    from botocore.config import Config
                    
                    # Configure bedrock client with extended timeouts
                    config = Config(
                        read_timeout=300,  # 5 minutes
                        connect_timeout=60,
                        retries={'max_attempts': 3}
                    )
                    bedrock = boto3.client('bedrock-runtime', 
                                         region_name=os.getenv("AWS_DEFAULT_REGION", "us-west-2"),
                                         config=config)
                    
                    # Prepare the message for Claude with image
                    message = {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": analysis_prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                    
                    # Call Claude Sonnet 4 with vision
                    response = bedrock.invoke_model(
                        modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 1000,
                            "temperature": 0.2,
                            "messages": [message]
                        })
                    )
                    
                    response_body = json.loads(response['body'].read())
                    response_text = response_body['content'][0]['text']
                    
                    print(f"Raw AI vision response for image {i+1}: {response_text}")
                    
                except Exception as vision_error:
                    print(f"Vision analysis failed for image {i+1}, falling back to Strands: {vision_error}")
                    # Fallback to text-only analysis
                    loop = asyncio.get_running_loop()
                    response_text = await loop.run_in_executor(self._executor, self._call_agent_sync, analysis_prompt)
                
                print(f"Raw AI response for image {i+1}: {response_text}")
                
                # Parse JSON response
                try:
                    # Remove markdown code blocks if present
                    clean_response = response_text.strip()
                    if clean_response.startswith('```json'):
                        clean_response = clean_response[7:]  # Remove ```json
                    if clean_response.endswith('```'):
                        clean_response = clean_response[:-3]  # Remove ```
                    clean_response = clean_response.strip()
                    
                    image_analysis = json.loads(clean_response)
                    print(f"Parsed analysis for image {i+1}: {image_analysis}")
                    
                    # Collect tags from this image
                    image_tags = image_analysis.get('tags', [])
                    all_tags.extend(image_tags)
                    
                    individual_analyses.append({
                        'image_index': i+1,
                        'image_url': image_url,
                        'analysis': image_analysis
                    })
                    
                    print(f"Tags from image {i+1}: {image_tags}")
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parsing failed for image {i+1}: {e}")
                    print(f"Raw response was: {response_text}")
                    # Add fallback tags for this image
                    fallback_tags = ['image_processed', 'analysis_error']
                    all_tags.extend(fallback_tags)
                    individual_analyses.append({
                        'image_index': i+1,
                        'image_url': image_url,
                        'analysis': {'error': 'Failed to parse AI response', 'raw_response': response_text}
                    })
            
            # Remove duplicates and create final tag list
            unique_tags = list(set(all_tags))
            print(f"\n=== FINAL ANALYSIS RESULTS ===")
            print(f"All collected tags: {all_tags}")
            print(f"Unique tags: {unique_tags}")
            print(f"Individual analyses count: {len(individual_analyses)}")
            
            # Create comprehensive summary
            summary = f"Analyzed {len(image_urls)} images. "
            if individual_analyses:
                damage_types = [analysis['analysis'].get('damage_type', 'unknown') for analysis in individual_analyses if 'analysis' in analysis and isinstance(analysis['analysis'], dict)]
                severities = [analysis['analysis'].get('severity', 'unknown') for analysis in individual_analyses if 'analysis' in analysis and isinstance(analysis['analysis'], dict)]
                
                if damage_types:
                    summary += f"Damage types found: {', '.join(set(damage_types))}. "
                if severities:
                    summary += f"Severity levels: {', '.join(set(severities))}."
            
            return {
                'tags': unique_tags,
                'analysis': {
                    'analysis_summary': summary,
                    'total_images': len(image_urls)
                },
                'individual_analyses': individual_analyses,
                'damage_severity': 'moderate'  # Could be determined from individual analyses
            }
            
        except Exception as e:
            print(f"ERROR analyzing images for {claim_id}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'tags': ['analysis_error'],
                'analysis': {'analysis_summary': f'Error analyzing images: {str(e)}'},
                'damage_severity': 'unknown'
            }
    
    def _download_video(self, s3_url: str) -> bytes:
        """Download video from S3 and return bytes"""
        try:
            presigned_url = self._get_presigned_url(s3_url)
            if not presigned_url:
                return None
            
            print(f"Downloading video from: {presigned_url}")
            response = requests.get(presigned_url, timeout=120)  # Longer timeout for videos
            response.raise_for_status()
            
            print(f"Successfully downloaded video, size: {len(response.content)} bytes")
            return response.content
            
        except Exception as e:
            print(f"Error downloading video from {s3_url}: {e}")
            return None
    async def analyze_videos(self, claim_id: str, video_urls: list) -> dict:
        """Analyze claim videos using Nova 2 Lite with actual video content"""
        
        print(f"\n=== STARTING VIDEO ANALYSIS WITH NOVA 2 LITE FOR CLAIM {claim_id} ===")
        print(f"Total videos to analyze: {len(video_urls)}")
        
        if not video_urls:
            print("No videos to analyze")
            return {
                'tags': [],
                'analysis': {'analysis_summary': 'No videos to analyze'},
                'video_quality': 'unknown'
            }
        
        all_tags = []
        individual_analyses = []
        
        try:
            # Analyze each video individually
            for i, video_url in enumerate(video_urls):
                print(f"\n--- Analyzing Video {i+1}/{len(video_urls)} ---")
                print(f"Video URL: {video_url}")
                
                # Download actual video content
                video_bytes = self._download_video(video_url)
                if not video_bytes:
                    print(f"Failed to download video {i+1}, skipping...")
                    individual_analyses.append({
                        'video_index': i+1,
                        'video_url': video_url,
                        'analysis': {'error': 'Failed to download video'}
                    })
                    continue
                
                # Use Nova 2 Lite for video analysis
                try:
                    from botocore.config import Config
                    
                    # Configure bedrock client with extended timeouts for video processing
                    config = Config(
                        read_timeout=600,  # 10 minutes for video analysis
                        connect_timeout=60,
                        retries={'max_attempts': 3}
                    )
                    bedrock = boto3.client('bedrock-runtime', region_name="us-east-1", config=config)
                    
                    user_prompt = f"""You are Nova 2 Lite analyzing an MP4 insurance claim video for claim {claim_id}.

This is video {i+1} of {len(video_urls)}.

Analyze the video and identify:
1. Primary damage type (collision, weather, fire, vandalism, water)
2. Damage severity (minor damage, moderate damage, severe damage)
3. Video quality (poor quality, good quality, excellent quality)
4. Consistency with typical claim scenarios (consistent with scenario, questionable for scenario, suspicious scenario)
5. Temporal analysis of damage progression (max 15 words)
6. Analysis summary (max 30 words)

Return ONLY valid JSON:
{{
    "damage_type": "",
    "severity": "",
    "video_quality": "",
    "consistency": "",
    "temporal_analysis": "",
    "analysis_summary": ""
}}"""
                    
                    response = bedrock.converse(
                        modelId="global.amazon.nova-2-lite-v1:0",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"text": user_prompt},
                                    {
                                        "video": {
                                            "format": "mp4",
                                            "source": {
                                                "bytes": video_bytes
                                            }
                                        }
                                    }
                                ]
                            }
                        ],
                        additionalModelRequestFields={
                            "reasoningConfig": {
                                "type": "enabled",
                                "maxReasoningEffort": "medium"
                            }
                        }
                    )
                    
                    # Parse Nova 2 Lite response - handle reasoning content
                    content_list = response["output"]["message"]["content"]
                    analysis_text = None
                    
                    for content in content_list:
                        if "text" in content:
                            analysis_text = content["text"]
                            break
                    
                    if not analysis_text:
                        raise ValueError("Nova response did not contain text")
                        
                    print(f"Raw Nova 2 Lite response for video {i+1}: {analysis_text}")
                    
                except Exception as nova_error:
                    print(f"Nova 2 Lite analysis failed for video {i+1}: {nova_error}")
                    # Fallback to text-only analysis
                    analysis_text = '{"tags": ["video_processed", "analysis_error"], "analysis_summary": "Video analysis failed"}'
                
                # Parse JSON response
                try:
                    # Remove markdown code blocks if present
                    clean_analysis = analysis_text.strip()
                    if clean_analysis.startswith('```json'):
                        clean_analysis = clean_analysis[7:]  # Remove ```json
                    if clean_analysis.endswith('```'):
                        clean_analysis = clean_analysis[:-3]  # Remove ```
                    clean_analysis = clean_analysis.strip()
                    
                    video_analysis = json.loads(clean_analysis)
                    print(f"Parsed analysis for video {i+1}: {video_analysis}")
                    
                    # Collect tags from video analysis - just extract the main values
                    video_tags = []
                    
                    # Extract the main field values as tags
                    damage_type = video_analysis.get('damage_type', '')
                    severity = video_analysis.get('severity', '')
                    video_quality = video_analysis.get('video_quality', '')
                    consistency = video_analysis.get('consistency', '')
                    
                    # Add the actual values as tags (clean format)
                    if damage_type:
                        video_tags.append(damage_type.lower().replace(' ', '_'))
                    if severity:
                        video_tags.append(severity.lower().replace(' ', '_'))
                    if video_quality:
                        video_tags.append(video_quality.lower().replace(' ', '_'))
                    if consistency:
                        video_tags.append(consistency.lower().replace(' ', '_'))
                    
                    all_tags.extend(video_tags)
                    
                    # Add tags to the analysis
                    video_analysis['tags'] = video_tags
                    
                    individual_analyses.append({
                        'video_index': i+1,
                        'video_url': video_url,
                        'video_size_bytes': len(video_bytes),
                        'analysis': video_analysis
                    })
                    
                    print(f"Tags from video {i+1}: {video_tags}")
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parsing failed for video {i+1}: {e}")
                    print(f"Raw response was: {analysis_text}")
                    # Add fallback tags for this video
                    fallback_tags = ['video_processed', 'analysis_error']
                    all_tags.extend(fallback_tags)
                    individual_analyses.append({
                        'video_index': i+1,
                        'video_url': video_url,
                        'analysis': {'error': 'Failed to parse AI response', 'raw_response': analysis_text}
                    })
                
                # Clean up memory
                del video_bytes
            
            # Remove duplicates and create final tag list
            unique_tags = list(set(all_tags))
            print(f"\n=== FINAL VIDEO ANALYSIS RESULTS ===")
            print(f"All collected tags: {all_tags}")
            print(f"Unique tags: {unique_tags}")
            print(f"Individual analyses count: {len(individual_analyses)}")
            
            # Create comprehensive summary
            summary = f"Analyzed {len(video_urls)} videos using Nova 2 Lite. "
            if individual_analyses:
                damage_types = [analysis['analysis'].get('damage_type', 'unknown') for analysis in individual_analyses if 'analysis' in analysis and isinstance(analysis['analysis'], dict)]
                severities = [analysis['analysis'].get('severity', 'unknown') for analysis in individual_analyses if 'analysis' in analysis and isinstance(analysis['analysis'], dict)]
                
                if damage_types:
                    summary += f"Damage types found: {', '.join(set(damage_types))}. "
                if severities:
                    summary += f"Severity levels: {', '.join(set(severities))}."
            
            return {
                'tags': unique_tags,
                'analysis': {
                    'analysis_summary': summary,
                    'total_videos': len(video_urls)
                },
                'individual_analyses': individual_analyses,
                'video_quality': 'good'  # Could be determined from individual analyses
            }
            
        except Exception as e:
            print(f"ERROR analyzing videos for {claim_id}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'tags': ['analysis_error'],
                'analysis': {'analysis_summary': f'Error analyzing videos: {str(e)}'},
                'video_quality': 'unknown'
            }
    
    def _download_transcript(self, s3_url: str) -> str:
        """Download transcript text from S3"""
        try:
            presigned_url = self._get_presigned_url(s3_url)
            if not presigned_url:
                return None
            
            print(f"Downloading transcript from: {presigned_url}")
            response = requests.get(presigned_url, timeout=30)
            response.raise_for_status()
            
            # Get text content
            transcript_text = response.text
            print(f"Successfully downloaded transcript, length: {len(transcript_text)} chars")
            return transcript_text
            
        except Exception as e:
            print(f"Error downloading transcript from {s3_url}: {e}")
            return None

    async def analyze_audio_transcripts(self, claim_id: str, transcript_urls: list, audio_urls: list) -> dict:
        """Analyze call transcripts and audio by downloading actual transcript content"""
        
        print(f"\n=== STARTING AUDIO/TRANSCRIPT ANALYSIS FOR CLAIM {claim_id} ===")
        print(f"Transcript files: {len(transcript_urls)}")
        print(f"Audio files: {len(audio_urls)}")
        
        if not transcript_urls and not audio_urls:
            print("No audio or transcripts to analyze")
            return {
                'tags': [],
                'analysis': {'analysis_summary': 'No audio or transcripts to analyze'},
                'fraud_risk': 'unknown'
            }
        
        all_tags = []
        individual_analyses = []
        
        try:
            # Analyze each transcript individually
            for i, transcript_url in enumerate(transcript_urls):
                print(f"\n--- Analyzing Transcript {i+1}/{len(transcript_urls)} ---")
                print(f"Transcript URL: {transcript_url}")
                
                # Download actual transcript content
                transcript_text = self._download_transcript(transcript_url)
                if not transcript_text:
                    print(f"Failed to download transcript {i+1}, skipping...")
                    individual_analyses.append({
                        'transcript_index': i+1,
                        'transcript_url': transcript_url,
                        'analysis': {'error': 'Failed to download transcript'}
                    })
                    continue
                
                print(f"Transcript content preview: {transcript_text[:200]}...")
                
                analysis_prompt = f"""
                Analyze this insurance claim call transcript for claim {claim_id}.
                
                This is transcript {i+1} of {len(transcript_urls)} total transcripts.
                
                TRANSCRIPT CONTENT:
                {transcript_text}
                
                Analyze the conversation and identify:
                1. Caller emotional state (calm, distressed, angry, suspicious)
                2. Story consistency (consistent, minor_inconsistencies, major_inconsistencies)
                3. Fraud indicators (none, potential, likely)
                4. Information completeness (complete, partial, vague)
                5. Caller credibility (high, medium, low)
                
                Return ONLY valid JSON with these exact fields:
                {{
                    "tags": ["emotional_state", "story_consistency", "fraud_risk", "information_quality"],
                    "emotional_state": "calm/distressed/angry/suspicious",
                    "story_consistency": "consistent/minor_inconsistencies/major_inconsistencies",
                    "fraud_risk": "none/potential/likely",
                    "information_quality": "complete/partial/vague",
                    "credibility": "high/medium/low",
                    "analysis_summary": "Brief summary of key findings from this transcript"
                }}
                
                Use specific tags from these lists:
                Emotional: calm, distressed, angry, suspicious, cooperative, uncooperative
                Consistency: story_consistent, minor_inconsistencies, major_inconsistencies, contradictory
                Fraud: no_fraud_indicators, potential_fraud, likely_fraud, fraud_red_flags
                Quality: complete_information, partial_information, vague_details, missing_details
                """
                
                # Use Strands agent to analyze transcript content
                loop = asyncio.get_running_loop()
                response_text = await loop.run_in_executor(self._executor, self._call_agent_sync, analysis_prompt)
                
                print(f"Raw AI response for transcript {i+1}: {response_text}")
                
                # Parse JSON response
                try:
                    # Remove markdown code blocks if present
                    clean_response = response_text.strip()
                    if clean_response.startswith('```json'):
                        clean_response = clean_response[7:]  # Remove ```json
                    if clean_response.endswith('```'):
                        clean_response = clean_response[:-3]  # Remove ```
                    clean_response = clean_response.strip()
                    
                    transcript_analysis = json.loads(clean_response)
                    print(f"Parsed analysis for transcript {i+1}: {transcript_analysis}")
                    
                    # Collect tags from this transcript
                    transcript_tags = transcript_analysis.get('tags', [])
                    all_tags.extend(transcript_tags)
                    
                    individual_analyses.append({
                        'transcript_index': i+1,
                        'transcript_url': transcript_url,
                        'content_length': len(transcript_text),
                        'analysis': transcript_analysis
                    })
                    
                    print(f"Tags from transcript {i+1}: {transcript_tags}")
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parsing failed for transcript {i+1}: {e}")
                    print(f"Raw response was: {response_text}")
                    # Add fallback tags for this transcript
                    fallback_tags = ['transcript_processed', 'analysis_error']
                    all_tags.extend(fallback_tags)
                    individual_analyses.append({
                        'transcript_index': i+1,
                        'transcript_url': transcript_url,
                        'analysis': {'error': 'Failed to parse AI response', 'raw_response': response_text}
                    })
            
            # Remove duplicates and create final tag list
            unique_tags = list(set(all_tags))
            print(f"\n=== FINAL TRANSCRIPT ANALYSIS RESULTS ===")
            print(f"All collected tags: {all_tags}")
            print(f"Unique tags: {unique_tags}")
            print(f"Individual analyses count: {len(individual_analyses)}")
            
            # Create comprehensive summary
            summary = f"Analyzed {len(transcript_urls)} transcripts. "
            if individual_analyses:
                fraud_risks = [analysis['analysis'].get('fraud_risk', 'unknown') for analysis in individual_analyses if 'analysis' in analysis and isinstance(analysis['analysis'], dict)]
                emotional_states = [analysis['analysis'].get('emotional_state', 'unknown') for analysis in individual_analyses if 'analysis' in analysis and isinstance(analysis['analysis'], dict)]
                
                if fraud_risks:
                    summary += f"Fraud risk levels: {', '.join(set(fraud_risks))}. "
                if emotional_states:
                    summary += f"Caller states: {', '.join(set(emotional_states))}."
            
            return {
                'tags': unique_tags,
                'analysis': {
                    'analysis_summary': summary,
                    'total_transcripts': len(transcript_urls),
                    'total_audio_files': len(audio_urls)
                },
                'individual_analyses': individual_analyses,
                'fraud_risk': 'low'  # Could be determined from individual analyses
            }
            
        except Exception as e:
            print(f"ERROR analyzing transcripts for {claim_id}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'tags': ['analysis_error'],
                'analysis': {'analysis_summary': f'Error analyzing transcripts: {str(e)}'},
                'fraud_risk': 'unknown'
            }

async def tag_s3_objects_individual(individual_analyses: list, url_key: str):
    """Tag each S3 object with its individual analysis results"""
    s3 = boto3.client('s3')
    
    for analysis in individual_analyses:
        try:
            file_url = analysis[url_key]  # 'image_url', 'video_url', etc.
            file_tags = analysis['analysis'].get('tags', [])
            file_index = analysis.get('image_index', analysis.get('video_index', analysis.get('transcript_index', 1)))
            
            # Parse S3 URL
            parts = file_url.replace('s3://', '').split('/', 1)
            bucket, key = parts[0], parts[1]
            
            # Create tag set with file-specific prefix
            tag_set = [
                {'Key': 'analysis_status', 'Value': 'completed'},
                {'Key': 'file_index', 'Value': str(file_index)}
            ]
            
            # Add individual file tags (S3 limit of 10 tags total)
            for i, tag in enumerate(file_tags[:8]):  # Leave room for status and index
                tag_set.append({'Key': f'file_{file_index}_tag_{i}', 'Value': tag})
            
            s3.put_object_tagging(
                Bucket=bucket,
                Key=key,
                Tagging={'TagSet': tag_set}
            )
            
        except Exception as e:
            print(f"Error tagging S3 object {analysis.get(url_key, 'unknown')}: {e}")
