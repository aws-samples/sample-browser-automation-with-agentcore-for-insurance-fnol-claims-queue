import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

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

# ---------- analyzer ----------
class ComplexityAnalyzer:
    def __init__(self):
        # Ensure Bedrock region (override from env if you prefer)
        os.environ.setdefault("AWS_DEFAULT_REGION", "us-west-2")

        self._executor = ThreadPoolExecutor(max_workers=1)

        # Build a Bedrock model object for Strands
        self.model = BedrockModel(
            model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-west-2"),
            temperature=0.2,
        )

        self.agent = Agent(
            name="Claims Complexity Analyzer",
            model=self.model,
            system_prompt=(
                "You are a Claims Complexity Analyzer specialist with expertise in:\n"
                "- Evaluating insurance claims for complexity based on multiple factors\n"
                "- Determining if claims require detailed human review or can be auto-processed\n"
                "- Analyzing damage amounts, evidence volume, and claim types\n"
                "- Making recommendations for claim routing and processing\n\n"
                "Your job is to analyze each claim and determine if it is COMPLEX or SIMPLE:\n\n"
                'COMPLEX claims should be routed to "Needs Review" status and require human adjuster review.\n'
                'SIMPLE claims can be auto-resolved and marked as "Resolved" status.\n\n'
                "Consider these factors:\n"
                "1. Damage amount (higher amounts = more complex)\n"
                "2. Evidence volume (more evidence = more complex)\n"
                "3. Claim type and subtype (certain types inherently more complex)\n"
                "4. Any unusual circumstances\n\n"
                "Always provide clear reasoning for your decision. Be conservative - when in doubt, mark as COMPLEX."
            ),
            tools=[analyze_damage_amount, analyze_evidence_volume, analyze_claim_type],
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
            "Please analyze this insurance claim for complexity:\n\n"
            f"Claim ID: {claim['id']}\n"
            f"Type: {claim['type']} - {claim['subtype']}\n"
            f"Estimated Damage: ${claim['estimated_damage']:,.2f}\n"
            f"Evidence: {claim['evidence']['images']} images, "
            f"{claim['evidence']['videos']} videos, {claim['evidence']['voice_recordings']} voice recordings\n"
            f"Description: {claim['description']}\n"
            f"Policy Holder: {claim['policy_holder']}\n\n"
            "Use the available tools to analyze:\n"
            "1. The damage amount\n"
            "2. The evidence volume\n"
            "3. The claim type and subtype\n\n"
            'Based on your analysis, determine if this is a COMPLEX or SIMPLE claim and provide reasoning.\n'
            'Respond with your final determination as either "Complex" or "Simple" along with your reasoning.'
        )

        try:
            loop = asyncio.get_running_loop()
            response_text = await loop.run_in_executor(self._executor, self._call_agent_sync, analysis_prompt)

            complexity = "Complex" if "Complex" in response_text else "Simple"
            return {"complexity": complexity, "reasoning": response_text}

        except Exception as e:
            # Fallback rules on failure
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
