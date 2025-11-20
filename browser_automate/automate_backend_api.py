#!/usr/bin/env python3
"""
Claims Automation using Backend API directly (no frontend needed)
"""

import requests
import time
from rich.console import Console

console = Console()

def automate_claims_backend():
    """Automate claims processing using backend API directly"""
    
    console.print("[cyan]🚀 Starting Claims Automation via Backend API[/cyan]")
    
    try:
        # Test backend connection
        response = requests.get("http://localhost:8000/api/claims")
        if response.status_code != 200:
            console.print("[red]❌ Backend not accessible[/red]")
            return
            
        claims = response.json()["claims"]
        console.print(f"[green]✅ Found {len(claims)} claims to process[/green]")
        
        # Process each claim
        for i, claim in enumerate(claims[:3], 1):  # Process first 3 claims
            console.print(f"\n[yellow]Processing Claim {i}: {claim['id']}[/yellow]")
            console.print(f"  Type: {claim['type']} - {claim['subtype']}")
            console.print(f"  Amount: ${claim['estimated_damage']:,}")
            console.print(f"  Status: {claim['status']}")
            
            # Analyze complexity
            complexity_data = {
                "claim_amount": claim["estimated_damage"],
                "description": claim["description"],
                "injury_severity": "moderate"
            }
            
            complexity_response = requests.post(
                "http://localhost:8000/analyze-complexity",
                json=complexity_data
            )
            
            if complexity_response.status_code == 200:
                complexity = complexity_response.json()
                console.print(f"  [blue]Complexity Score: {complexity['complexity_score']:.2f}[/blue]")
                console.print(f"  [blue]Recommendation: {complexity['recommendation']}[/blue]")
                
                # Simulate processing decision
                if complexity['complexity_score'] < 0.5:
                    console.print("  [green]✓ Auto-approved (Low complexity)[/green]")
                else:
                    console.print("  [yellow]⚠️ Flagged for manual review (High complexity)[/yellow]")
            
            time.sleep(1)  # Brief pause between claims
        
        console.print("\n[bold green]🎉 Claims automation completed successfully![/bold green]")
        
    except requests.exceptions.ConnectionError:
        console.print("[red]❌ Cannot connect to backend API at http://localhost:8000[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")

if __name__ == "__main__":
    automate_claims_backend()
