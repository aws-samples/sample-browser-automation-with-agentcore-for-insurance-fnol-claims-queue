#!/usr/bin/env python3
"""
Generate realistic claim evidence using Amazon Nova models
- Images: Amazon Nova Canvas
- Videos: Amazon Nova Reel  
- Call Transcripts: Amazon Nova Sonic (text generation)
"""

import boto3
import json
import os
import base64
import argparse
import time
import random
import asyncio
import sys
from datetime import datetime
from typing import Dict, List, Optional

def check_aws_credentials():
    """Automatically extract and set AWS credentials from AWS CLI config or SSO"""
    import subprocess
    
    try:
        # Try to get temporary credentials using AWS CLI (works for both regular and SSO)
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                              capture_output=True, text=True, check=True)
        
        # Get session credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials:
            os.environ['AWS_ACCESS_KEY_ID'] = credentials.access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = credentials.secret_key
            if credentials.token:
                os.environ['AWS_SESSION_TOKEN'] = credentials.token
            
            # Set region
            region = session.region_name or 'us-east-1'
            os.environ['AWS_DEFAULT_REGION'] = region
            
            print("✓ AWS credentials extracted successfully")
        else:
            raise Exception("No credentials found")
            
    except Exception:
        print("❌ Could not extract AWS credentials.")
        print("Run: aws configure  OR  aws configure sso")
        sys.exit(1)

class ClaimEvidenceGenerator:
    def __init__(self, region='us-west-2', s3_bucket=None):
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.bedrock_east = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.s3 = boto3.client('s3', region_name='us-east-1')
        self.region = region
        self.s3_bucket = s3_bucket or self._create_s3_bucket()
        self.output_dir = "generated_evidence"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _create_s3_bucket(self):
        """Create S3 bucket for video storage"""
        bucket_name = f"claims-evidence-{random.randint(10000, 99999)}"
        try:
            self.s3.create_bucket(Bucket=bucket_name)
            print(f"✓ Created S3 bucket: {bucket_name}")
            return bucket_name
        except Exception as e:
            print(f"Warning: Could not create S3 bucket: {e}")
            return None
        
    def generate_images(self, claim_details: Dict[str, str], count: int = 3) -> List[str]:
        """Generate realistic claim images using Amazon Nova Canvas"""
        images = []
        topic = claim_details.get('topic', 'property damage')
        claim_num = claim_details.get('claim_number', 'CLM-001').replace('-', '_')
        
        for i in range(count):
            try:
                enhanced_prompt = f"High-resolution, realistic photograph of {topic}, insurance claim documentation style, clear lighting, professional quality, detailed damage visible"
                
                # Generate random seed for Nova Canvas
                seed = random.randint(0, 858993460)
                
                # Nova Canvas native request format
                native_request = {
                    "taskType": "TEXT_IMAGE",
                    "textToImageParams": {"text": enhanced_prompt},
                    "imageGenerationConfig": {
                        "seed": seed,
                        "quality": "standard",
                        "height": 1024,
                        "width": 1024,
                        "numberOfImages": 1,
                    },
                }
                
                try:
                    # Try Nova Canvas in us-east-1
                    response = self.bedrock_east.invoke_model(
                        modelId="amazon.nova-canvas-v1:0",
                        body=json.dumps(native_request)
                    )
                    
                    result = json.loads(response['body'].read())
                    image_data = result['images'][0]
                    
                except Exception as nova_error:
                    print(f"Nova Canvas failed, trying Titan: {nova_error}")
                    # Fallback to Titan Image Generator
                    response = self.bedrock.invoke_model(
                        modelId='amazon.titan-image-generator-v1',
                        body=json.dumps({
                            "taskType": "TEXT_IMAGE",
                            "textToImageParams": {
                                "text": enhanced_prompt
                            },
                            "imageGenerationConfig": {
                                "numberOfImages": 1,
                                "height": 1024,
                                "width": 1024,
                                "cfgScale": 8.0
                            }
                        })
                    )
                    
                    result = json.loads(response['body'].read())
                    image_data = result['images'][0]
                
                # Save image with claim number naming
                filename = f"{claim_num}_image_{i+1}.png"
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(base64.b64decode(image_data))
                
                images.append(filepath)
                print(f"✓ Generated image: {filename}")
                
            except Exception as e:
                print(f"Error generating image {i+1}: {e}")
                
        return images
    
    def generate_videos(self, claim_details: Dict[str, str], count: int = 2) -> List[str]:
        """Generate realistic claim videos using Amazon Nova Reel async API"""
        videos = []
        topic = claim_details.get('topic', 'property damage')
        claim_num = claim_details.get('claim_number', 'CLM-001').replace('-', '_')
        
        if not self.s3_bucket:
            print("⚠ No S3 bucket available, generating video scripts instead")
            return self._generate_video_scripts(claim_details, count)
        
        for i in range(count):
            try:
                # Enhanced prompt for realistic claim video
                enhanced_prompt = f"Professional insurance documentation video of {topic}, steady camera movement showing damage clearly, assessment perspective"
                
                # Generate random seed
                seed = random.randint(0, 2147483646)
                
                # Configure video generation request
                model_input = {
                    "taskType": "TEXT_VIDEO",
                    "textToVideoParams": {"text": enhanced_prompt},
                    "videoGenerationConfig": {
                        "fps": 24,
                        "durationSeconds": 6,
                        "dimension": "1280x720",
                        "seed": seed,
                    },
                }
                
                # S3 output configuration
                output_s3_uri = f"s3://{self.s3_bucket}/videos/"
                output_config = {"s3OutputDataConfig": {"s3Uri": output_s3_uri}}
                
                # Start async video generation job
                response = self.bedrock_east.start_async_invoke(
                    modelId="amazon.nova-reel-v1:0",
                    modelInput=model_input,
                    outputDataConfig=output_config
                )
                
                invocation_arn = response["invocationArn"]
                print(f"⏳ Video generation job started: {invocation_arn}")
                print("   Waiting for completion (Nova Reel typically takes 3-5 minutes)...")
                
                # Wait indefinitely until completion
                wait_time = 0
                
                while True:
                    job_status = self.bedrock_east.get_async_invoke(invocationArn=invocation_arn)
                    status = job_status["status"]
                    
                    if status == "Completed":
                        bucket_uri = job_status["outputDataConfig"]["s3OutputDataConfig"]["s3Uri"]
                        
                        # Download video locally with claim number naming
                        local_video_filename = f"{claim_num}_video_{i+1}.mp4"
                        local_video_path = os.path.join(self.output_dir, local_video_filename)
                        
                        try:
                            # Download from S3
                            s3_client = boto3.client('s3', region_name='us-east-1')
                            bucket_name = self.s3_bucket
                            s3_key = f"videos/{invocation_arn.split('/')[-1]}/output.mp4"
                            
                            s3_client.download_file(bucket_name, s3_key, local_video_path)
                            print(f"✓ Downloaded video: {local_video_filename}")
                            
                            videos.append(local_video_path)
                            
                        except Exception as download_error:
                            print(f"Warning: Could not download video: {download_error}")
                            
                            # Create reference file as fallback
                            filename = f"{claim_num}_video_{i+1}.txt"
                            filepath = os.path.join(self.output_dir, filename)
                            
                            with open(filepath, 'w') as f:
                                f.write(f"=== Generated Video Reference ===\n")
                                f.write(f"S3 Location: {bucket_uri}/output.mp4\n")
                                f.write(f"Prompt: {enhanced_prompt}\n")
                                f.write(f"Duration: 6 seconds\n")
                                f.write(f"Resolution: 1280x720\n")
                                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                f.write(f"Total wait time: {wait_time} seconds\n")
                                f.write(f"\nTo download:\n")
                                f.write(f"aws s3 cp {bucket_uri}/output.mp4 ./{local_video_filename}\n")
                            
                            videos.append(filepath)
                        
                        print(f"  Completed in {wait_time}s")
                        break
                        
                    elif status == "Failed":
                        error_msg = job_status.get('failureMessage', 'Unknown error')
                        raise Exception(f"Video generation failed: {error_msg}")
                    else:
                        # Show progress every 30 seconds
                        if wait_time % 30 == 0:
                            minutes = wait_time // 60
                            seconds = wait_time % 60
                            print(f"  Status: {status} - Elapsed: {minutes}m {seconds}s")
                        
                        time.sleep(10)
                        wait_time += 10
                    
            except Exception as e:
                print(f"Error generating video {i+1}: {e}")
                # Create fallback script
                fallback = self._generate_video_scripts(claim_details, 1)
                if fallback:
                    videos.extend(fallback)
                
        return videos
    
    def _generate_video_scripts(self, claim_details: Dict[str, str], count: int) -> List[str]:
        """Generate video scripts as fallback"""
        scripts = []
        topic = claim_details.get('topic', 'property damage')
        claim_num = claim_details.get('claim_number', 'CLM-001').replace('-', '_')
        
        for i in range(count):
            filename = f"{claim_num}_video_{i+1}.txt"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w') as f:
                f.write(f"VIDEO SCRIPT FALLBACK\nPrompt: {topic}\nNote: Use with video recording equipment")
            
            scripts.append(filepath)
            print(f"✓ Generated video script fallback: {filename}")
        
        return scripts
    
    def parse_input_with_claude(self, input_text: str) -> Dict[str, str]:
        """Use Claude Sonnet to parse input and extract claim details"""
        try:
            prompt = f"""
            Parse this insurance claim input and extract the following information:
            Input: "{input_text}"
            
            Extract and return ONLY a JSON object with these fields:
            - topic: The main incident/damage type
            - policyholder_name: Full name of the policy holder
            - policy_number: Policy number if mentioned
            - claim_number: Claim number if mentioned  
            - gender: "male" or "female" based on the name (guess if needed)
            
            Return only valid JSON, no other text.
            """
            
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}]
                }),
                contentType="application/json"
            )
            
            result = json.loads(response['body'].read())
            content = result['content'][0]['text'].strip()
            
            # Parse the JSON response
            parsed_data = json.loads(content)
            print(f"✓ Parsed claim details: {parsed_data}")
            return parsed_data
            
        except Exception as e:
            print(f"Error parsing input with Claude: {e}")
            # Fallback parsing
            return {
                "topic": input_text,
                "policyholder_name": "John Smith",
                "policy_number": "POL-12345",
                "claim_number": "CLM-001",
                "gender": "male"
            }
    
    def generate_call_transcripts(self, claim_details: Dict[str, str], count: int = 1) -> List[str]:
        """Generate realistic FNOL call transcripts with single voice (policyholder only)"""
        transcripts = []
        
        for i in range(count):
            try:
                # Create FNOL call prompt for single voice
                prompt = f"""
                Generate a realistic First Notice of Loss (FNOL) call transcript where the policyholder calls to report a claim.
                
                Details:
                - Policyholder: {claim_details.get('policyholder_name', 'John Smith')}
                - Policy Number: {claim_details.get('policy_number', 'POL-12345')}
                - Claim Number: {claim_details.get('claim_number', 'CLM-001')}
                - Incident: {claim_details.get('topic', 'property damage')}
                
                Format as a single voice monologue where the policyholder:
                1. Introduces themselves with name and policy number
                2. Explains what happened in detail
                3. Describes the damage/loss
                4. Mentions when it occurred
                5. Provides their contact information
                
                Make it sound natural and conversational, like someone calling their insurance company.
                Keep it under 2000 characters for TTS.
                """
                
                response = self.bedrock.invoke_model(
                    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "messages": [{"role": "user", "content": prompt}]
                    }),
                    contentType="application/json"
                )
                
                result = json.loads(response['body'].read())
                transcript_text = result['content'][0]['text']
                
                # Save transcript with claim number
                claim_num = claim_details.get('claim_number', 'CLM-001').replace('-', '_')
                filename = f"{claim_num}_transcript_{i+1}.txt"
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, 'w') as f:
                    f.write(f"FNOL Call Transcript\n")
                    f.write(f"Claim Number: {claim_details.get('claim_number', 'CLM-001')}\n")
                    f.write(f"Policyholder: {claim_details.get('policyholder_name', 'John Smith')}\n")
                    f.write(f"Policy Number: {claim_details.get('policy_number', 'POL-12345')}\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(transcript_text)
                
                transcripts.append(filepath)
                print(f"✓ Generated transcript: {filename}")
                
                # Generate voice audio for this transcript
                self._generate_voice_audio(transcript_text, claim_details, i+1)
                
            except Exception as e:
                print(f"Error generating transcript {i+1}: {e}")
                
        return transcripts
    

    def _generate_voice_audio(self, transcript_text: str, claim_details: Dict[str, str], call_number: int):
        """Generate voice audio using Amazon Polly with gender-appropriate voice"""
        try:
            # Generate single coherent conversation audio
            audio_file = asyncio.run(self._generate_polly_audio(transcript_text, claim_details, call_number))
            
            if audio_file:
                print(f"✓ Generated FNOL call audio: {audio_file}")
            else:
                self._create_audio_placeholder(claim_details, call_number, "FNOL audio generation failed")
                
        except Exception as e:
            print(f"Error generating voice audio for call {call_number}: {e}")
            self._create_audio_placeholder(claim_details, call_number, str(e))
    
    async def _generate_polly_audio(self, transcript_text: str, claim_details: Dict[str, str], call_number: int):
        """Generate realistic FNOL call audio using Amazon Polly Neural TTS with gender-appropriate voice"""
        print(f"=== Generating FNOL Call Audio: Call {call_number} ===")

        # Clean text for TTS
        cleaned = transcript_text.strip()
        if not cleaned:
            print("No usable speech content extracted.")
            return None

        try:
            import boto3
            import wave

            polly = boto3.client('polly', region_name='us-east-1')
            
            # Select voice based on gender
            gender = claim_details.get('gender', 'male').lower()
            voice_id = 'Matthew' if gender == 'male' else 'Joanna'
            
            print(f"Using Amazon Polly Neural TTS with {voice_id} voice...")
            
            # Use neural voice for more realistic speech
            response = polly.synthesize_speech(
                Text=cleaned,
                OutputFormat='pcm',
                VoiceId=voice_id,
                Engine='neural'
            )
            
            audio_raw = response['AudioStream'].read()
            print(f"Generated {len(audio_raw)} bytes of FNOL call audio")

            if not audio_raw:
                print("❌ No audio received from Polly")
                return None

            # Save WAV file with claim number naming
            claim_num = claim_details.get('claim_number', 'CLM-001').replace('-', '_')
            filename = f"{claim_num}_audio_{call_number}.wav"
            path = os.path.join(self.output_dir, filename)

            with wave.open(path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(audio_raw)

            print(f"✓ Saved FNOL call audio: {filename}")
            return filename
            
        except Exception as e:
            print(f"FNOL call audio generation failed: {e}")
            return None
    
    def _create_audio_placeholder(self, claim_details: Dict[str, str], call_number: int, error_msg: str):
        """Create placeholder file when audio generation fails"""
        claim_num = claim_details.get('claim_number', 'CLM-001').replace('-', '_')
        filename = f"{claim_num}_audio_error_{call_number}.txt"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(f"Audio Generation Error\n")
            f.write(f"Claim Number: {claim_details.get('claim_number', 'CLM-001')}\n")
            f.write(f"Call Number: {call_number}\n")
            f.write(f"Error: {error_msg}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print(f"✓ Created audio error placeholder: {filename}")
    
    
    def cleanup_s3_bucket(self):
        """Download any remaining files from S3 and delete the bucket"""
        if not self.s3_bucket:
            return
            
        try:
            print(f"🧹 Cleaning up S3 bucket: {self.s3_bucket}")
            
            # List and download any remaining files
            response = self.s3.list_objects_v2(Bucket=self.s3_bucket)
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    local_filename = os.path.basename(key)
                    local_path = os.path.join(self.output_dir, local_filename)
                    
                    try:
                        self.s3.download_file(self.s3_bucket, key, local_path)
                        print(f"✓ Downloaded: {local_filename}")
                    except Exception as e:
                        print(f"Warning: Could not download {key}: {e}")
            
            # Delete all objects in bucket
            if 'Contents' in response:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                self.s3.delete_objects(
                    Bucket=self.s3_bucket,
                    Delete={'Objects': objects_to_delete}
                )
            
            # Delete the bucket
            self.s3.delete_bucket(Bucket=self.s3_bucket)
            print(f"✓ Deleted S3 bucket: {self.s3_bucket}")
            
        except Exception as e:
            print(f"Warning: Could not clean up S3 bucket: {e}")
    
    def generate_complete_evidence_package(self, claim_details: Dict[str, str], images_count: int = 3, videos_count: int = 2, transcripts_count: int = 1) -> Dict:
        """Generate complete evidence package for a claim"""
        topic = claim_details.get('topic', 'property damage')
        print(f"🎬 Generating evidence package for: {topic}")
        print(f"📋 Claim Details: {claim_details}")
        print("-" * 50)
        
        # Generate all evidence types
        images = self.generate_images(claim_details, count=images_count)
        videos = self.generate_videos(claim_details, count=videos_count)
        transcripts = self.generate_call_transcripts(claim_details, count=transcripts_count)
        
        evidence_package = {
            "claim_details": claim_details,
            "generated_at": datetime.now().isoformat(),
            "evidence": {
                "images": images,
                "videos": videos,
                "call_transcripts": transcripts
            },
            "summary": {
                "total_images": len(images),
                "total_videos": len(videos),
                "total_transcripts": len(transcripts)
            }
        }
        
        # Save evidence manifest with claim number
        claim_num = claim_details.get('claim_number', 'CLM-001').replace('-', '_')
        manifest_file = f"{claim_num}_manifest.json"
        manifest_path = os.path.join(self.output_dir, manifest_file)
        
        with open(manifest_path, 'w') as f:
            json.dump(evidence_package, f, indent=2)
        
        print(f"\n✅ Evidence package generated successfully!")
        print(f"📁 Manifest saved: {manifest_path}")
        print(f"📊 Summary: {len(images)} images, {len(videos)} videos, {len(transcripts)} transcripts")
        
        return evidence_package

def main():
    # Check AWS credentials first
    check_aws_credentials()
    
    parser = argparse.ArgumentParser(description='Generate realistic claim evidence using Amazon Nova models')
    parser.add_argument('prompt', help='Claim description with details (e.g., "kitchen fire damage call by John Smith with Policy number POL-12345 Claim number CLM-001")')
    parser.add_argument('mode', choices=['all', 'image', 'video', 'audio'], 
                       help='Generation mode: all (complete package), image (images only), video (videos only), audio (call transcripts only)')
    parser.add_argument('--images', type=int, default=3, help='Number of images to generate')
    parser.add_argument('--videos', type=int, default=2, help='Number of videos to generate')
    parser.add_argument('--transcripts', type=int, default=1, help='Number of call transcripts to generate')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    parser.add_argument('--s3-bucket', help='S3 bucket for video storage (auto-generated if not provided)')
    
    args = parser.parse_args()
    
    generator = ClaimEvidenceGenerator(region=args.region, s3_bucket=args.s3_bucket)
    
    # Parse input with Claude to extract claim details
    claim_details = generator.parse_input_with_claude(args.prompt)
    
    print(f"🔍 Generating test data for:")
    print(f"   Policyholder: {claim_details.get('policyholder_name')}")
    print(f"   Policy Number: {claim_details.get('policy_number')}")
    print(f"   Claim Number: {claim_details.get('claim_number')}")
    print(f"   Incident: {claim_details.get('topic')}")
    print(f"   Voice: {claim_details.get('gender')} voice")
    print("-" * 50)
    
    try:
        if args.mode == 'all':
            generator.generate_complete_evidence_package(claim_details, args.images, args.videos, args.transcripts)
        elif args.mode == 'image':
            generator.generate_images(claim_details, args.images)
        elif args.mode == 'video':
            generator.generate_videos(claim_details, args.videos)
        elif args.mode == 'audio':
            generator.generate_call_transcripts(claim_details, args.transcripts)
    finally:
        # Always cleanup S3 bucket at the end
        generator.cleanup_s3_bucket()

if __name__ == "__main__":
    main()
