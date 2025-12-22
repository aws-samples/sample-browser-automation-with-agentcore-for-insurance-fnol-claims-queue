import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
import boto3

# ✅ correct Strands imports
from strands import Agent, tool
from strands.models import BedrockModel

# ---------- tools ----------
@tool(
    name="analyze_damage_amount",
    description="Analyze the estimated damage amount to determine if it requires complex review",
)
def analyze_damage_amount(estimated_damage: float) -> Dict[str, Any]:
    if estimated_damage > 30000:
        return {
            "complexity_factor": "high",
            "reason": f"High damage amount of ${estimated_damage:,.2f} requires detailed review",
        }
    elif estimated_damage > 15000:
        return {
            "complexity_factor": "medium",
            "reason": f"Moderate damage amount of ${estimated_damage:,.2f} may need review",
        }
    else:
        return {
            "complexity_factor": "low",
            "reason": f"Low damage amount of ${estimated_damage:,.2f} can be processed quickly",
        }

@tool(
    name="analyze_evidence_volume",
    description="Analyze the volume and type of evidence submitted with the claim",
)
def analyze_evidence_volume(evidence: Dict[str, int]) -> Dict[str, Any]:
    total = evidence.get("images", 0) + evidence.get("videos", 0) + evidence.get("voice_recordings", 0)
    if total > 10:
        return {
            "complexity_factor": "high",
            "reason": f"Large volume of evidence ({total} items) requires thorough review",
        }
    elif total > 5:
        return {
            "complexity_factor": "medium",
            "reason": f"Moderate evidence volume ({total} items) needs careful analysis",
        }
    else:
        return {
            "complexity_factor": "low",
            "reason": f"Limited evidence ({total} items) allows for quick processing",
        }

@tool(
    name="analyze_claim_type",
    description="Analyze the type and subtype of claim to determine complexity",
)
def analyze_claim_type(claim_type: str, subtype: str) -> Dict[str, Any]:
    complex_subtypes = ["Fire Damage", "Theft", "Flood", "Storm Damage"]
    if subtype in complex_subtypes:
        return {
            "complexity_factor": "high",
            "reason": f"{subtype} claims typically require specialized investigation",
        }
    elif claim_type == "Property":
        return {
            "complexity_factor": "medium",
            "reason": "Property claims often need detailed assessment",
        }
    else:
        return {
            "complexity_factor": "low",
            "reason": f"Standard {claim_type} - {subtype} claim with routine processing",
        }

@tool(
    name="analyze_evidence_tags",
    description="Analyze evidence tags from pre-analyzed images, videos, and audio to determine complexity factors",
)
def analyze_evidence_tags(claim_id: str) -> Dict[str, Any]:
    """Analyze evidence tags to determine complexity factors"""
    
    try:
        # Get evidence analysis from DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2'))
        table_name = os.getenv('CLAIMS_TABLE_NAME', 'Claims')
        table = dynamodb.Table(table_name)
        
        response = table.get_item(Key={'claim_id': claim_id})
        if 'Item' not in response:
            return {"complexity_factor": "unknown", "reason": "Claim not found", "evidence_score": 0}
        
        claim = response['Item']
        evidence_analysis = claim.get('evidence_analysis', {})
        
        complexity_indicators = []
        complexity_score = 0
        
        # Analyze image tags for damage patterns
        image_analysis = evidence_analysis.get('images', {})
        if image_analysis.get('status') == 'completed':
            image_tags = image_analysis.get('tags', [])
            
            # Look for severity indicators (exact tag matching)
            if 'severe' in image_tags:
                complexity_indicators.append("🔴 **[FROM IMAGES]** Severe damage detected in images")
                complexity_score += 4
            elif 'moderate' in image_tags:
                complexity_indicators.append("🟡 **[FROM IMAGES]** Moderate damage detected in images")
                complexity_score += 2
            
            # Look for damage types that require expertise
            high_complexity_damage = ['fire_damage', 'water_damage', 'weather_damage', 'theft_damage']
            if any(damage in image_tags for damage in high_complexity_damage):
                complexity_indicators.append("🔴 **[FROM IMAGES]** Complex damage type requiring specialized assessment")
                complexity_score += 3
            
            # Look for structural areas (property claims)
            structural_areas = ['roof', 'interior', 'windshield']
            if any(area in image_tags for area in structural_areas):
                complexity_indicators.append("🟡 **[FROM IMAGES]** Structural damage areas identified")
                complexity_score += 2
        
        # Analyze video tags for quality and consistency
        video_analysis = evidence_analysis.get('videos', {})
        if video_analysis.get('status') == 'completed':
            video_tags = video_analysis.get('tags', [])
            
            # Look for quality issues
            if 'poor' in video_tags:
                complexity_indicators.append("🟡 **[FROM VIDEOS]** Poor video quality requires manual review")
                complexity_score += 3
            
            # Look for consistency issues
            if 'questionable' in video_tags or 'suspicious' in video_tags:
                complexity_indicators.append("🔴 **[FROM VIDEOS]** Video evidence shows questionable elements")
                complexity_score += 4
        
        # Analyze audio/transcript tags for credibility and fraud indicators
        audio_analysis = evidence_analysis.get('audio', {})
        if audio_analysis.get('status') == 'completed':
            audio_tags = audio_analysis.get('tags', [])
            
            # Look for story consistency issues
            if 'major_inconsistencies' in audio_tags:
                complexity_indicators.append("🔴 **[FROM AUDIO]** Major story inconsistencies detected")
                complexity_score += 5
            elif 'minor_inconsistencies' in audio_tags:
                complexity_indicators.append("🟡 **[FROM AUDIO]** Minor story inconsistencies noted")
                complexity_score += 2
            
            # Look for explicit fraud indicators (exact matches only)
            if 'likely_fraud' in audio_tags or 'potential_fraud' in audio_tags or 'fraud_detected' in audio_tags:
                complexity_indicators.append("🔴 **[FROM AUDIO]** Fraud indicators detected in caller statements")
                complexity_score += 6
            
            # Look for credibility issues (exact matches only)
            if 'low_credibility' in audio_tags or 'not_credible' in audio_tags:
                complexity_indicators.append("🟡 **[FROM AUDIO]** Low caller credibility detected")
                complexity_score += 3
            
            # Look for positive indicators (exact matches only)
            if 'no_fraud_indicators' in audio_tags or 'story_consistent' in audio_tags or 'credible' in audio_tags:
                complexity_indicators.append("🟢 **[FROM AUDIO]** Credible account with consistent story")
                complexity_score = max(0, complexity_score - 2)  # Stronger positive signal
        
        # Determine overall complexity factor
        if complexity_score >= 6:
            complexity_factor = "high"
        elif complexity_score >= 3:
            complexity_factor = "medium"
        elif complexity_score >= 1:
            complexity_factor = "low"
        else:
            complexity_factor = "minimal"
        
        analyzed_count = len([k for k, v in evidence_analysis.items() if v.get('status') == 'completed'])
        
        return {
            "complexity_factor": complexity_factor,
            "reason": f"Evidence analysis reveals {len(complexity_indicators)} complexity factors: {'; '.join(complexity_indicators) if complexity_indicators else 'Standard evidence patterns with no significant issues'}",
            "evidence_score": complexity_score,
            "total_evidence_analyzed": analyzed_count,
            "indicators": complexity_indicators
        }
        
    except Exception as e:
        return {
            "complexity_factor": "unknown", 
            "reason": f"Error analyzing evidence: {str(e)}",
            "evidence_score": 0,
            "total_evidence_analyzed": 0
        }

# ---------- analyzer ----------
class ComplexityAnalyzer:
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
            name="Claims Complexity Analyzer",
            model=self.model,
            system_prompt=(
                "You are a Claims Complexity Analyzer with access to comprehensive evidence analysis.\n"
                "You can analyze:\n"
                "- Pre-analyzed image tags showing damage severity and type\n"
                "- Video analysis tags showing damage progression and quality\n"
                "- Audio/transcript analysis tags showing caller state and story consistency\n"
                "- Cross-evidence consistency and fraud indicators\n\n"
                "Use the analyze_evidence_tags tool to get detailed evidence analysis before making complexity decisions.\n"
                "Consider both traditional factors (damage amount, claim type) AND evidence analysis results.\n"
                "Be more confident in your decisions when comprehensive evidence analysis is available.\n\n"
                "Your job is to analyze each claim and determine if it is COMPLEX or SIMPLE:\n\n"
                'COMPLEX claims should be routed to "Needs Review" status and require human adjuster review.\n'
                'SIMPLE claims can be auto-resolved and marked as "Resolved" status.\n\n'
                "Consider these factors:\n"
                "1. Damage amount (higher amounts = more complex)\n"
                "2. Evidence volume (more evidence = more complex)\n"
                "3. Claim type and subtype (certain types inherently more complex)\n"
                "4. Evidence analysis results (fraud indicators, inconsistencies, severe damage)\n\n"
                "IMPORTANT: If evidence analysis shows high damage severity, inconsistencies, or fraud indicators, "
                "mark as COMPLEX regardless of other factors.\n\n"
                "Always provide clear reasoning for your decision. Be conservative - when in doubt, mark as COMPLEX."
            ),
            tools=[analyze_damage_amount, analyze_evidence_volume, analyze_claim_type, analyze_evidence_tags],
        )

    def _call_agent_sync(self, prompt: str) -> str:
        """Call the agent synchronously and return text content."""
        try:
            result = self.agent(prompt)
        except TypeError:
            result = self.agent.run(prompt)

        return getattr(result, "content", str(result))

    async def analyze_claim(self, claim: Dict[str, Any]) -> Dict[str, str]:
        """
        Analyze a claim and return complexity assessment.
        Keeps the async signature; executes the agent in a thread.
        """
        analysis_prompt = (
            f"Analyze claim {claim['claim_id']} for complexity:\n\n"
            f"Basic Information:\n"
            f"- Type: {claim['type']} - {claim['subtype']}\n"
            f"- Estimated Damage: ${claim['estimated_damage']:,.2f}\n"
            f"- Evidence Counts: {claim['evidence']['images']} images, "
            f"{claim['evidence']['videos']} videos, {claim['evidence']['voice_recordings']} recordings\n"
            f"- Description: {claim['description']}\n\n"
            f"IMPORTANT: Use the analyze_evidence_tags tool to examine the detailed evidence analysis "
            f"for claim {claim['claim_id']}. This will provide:\n"
            f"- Damage severity from image analysis\n"
            f"- Story consistency from transcript analysis\n"
            f"- Fraud indicators from cross-evidence analysis\n"
            f"- Overall evidence quality assessment\n\n"
            f"Use all available tools to analyze:\n"
            f"1. The damage amount (analyze_damage_amount)\n"
            f"2. The evidence volume (analyze_evidence_volume)\n"
            f"3. The claim type and subtype (analyze_claim_type)\n"
            f"4. The evidence analysis results (analyze_evidence_tags)\n\n"
            f"Base your complexity determination on BOTH traditional factors AND comprehensive evidence analysis.\n"
            f"If evidence analysis shows high damage severity, inconsistencies, or fraud indicators, "
            f"mark as COMPLEX regardless of other factors.\n\n"
            f"Provide detailed reasoning and end with: FINAL DETERMINATION: [Complex or Simple]"
        )

        try:
            loop = asyncio.get_running_loop()
            response_text = await loop.run_in_executor(self._executor, self._call_agent_sync, analysis_prompt)

            # Parse structured final determination
            if "FINAL DETERMINATION:" in response_text:
                determination = response_text.split("FINAL DETERMINATION:")[-1].strip().upper()
                complexity = "Complex" if "COMPLEX" in determination else "Simple"
            else:
                # Fallback to current logic
                complexity = "Complex" if "COMPLEX" in response_text.upper() else "Simple"
            
            return {"complexity": complexity, "reasoning": response_text}

        except Exception as e:
            # Enhanced fallback with evidence consideration
            print(f"Agent analysis failed: {e}")
            
            # Try to get evidence analysis directly
            try:
                evidence_result = analyze_evidence_tags(claim['claim_id'])
                if evidence_result['complexity_factor'] == 'high' or evidence_result.get('evidence_score', 0) > 5:
                    return {
                        "complexity": "Complex",
                        "reasoning": f"Fallback analysis with evidence: {evidence_result['reason']}"
                    }
            except:
                pass
            
            # Traditional fallback
            if (claim.get("estimated_damage", 0) > 20000 or 
                sum(claim.get("evidence", {}).values()) > 8):
                return {
                    "complexity": "Complex",
                    "reasoning": "Fallback analysis: High damage amount or significant evidence volume"
                }
            else:
                return {
                    "complexity": "Simple", 
                    "reasoning": "Fallback analysis: Standard claim parameters"
                }
            print(f"Agent analysis failed: {e}")
            if (
                claim.get("estimated_damage", 0) > 20000
                or sum(claim.get("evidence", {}).values()) > 8
                or claim.get("subtype") in ["Fire Damage", "Theft", "Flood"]
            ):
                return {
                    "complexity": "Complex",
                    "reasoning": "Fallback analysis: High damage amount, significant evidence, or complex claim type detected",
                }
            else:
                return {
                    "complexity": "Simple",
                    "reasoning": "Fallback analysis: Standard claim with moderate damage and evidence",
                }
