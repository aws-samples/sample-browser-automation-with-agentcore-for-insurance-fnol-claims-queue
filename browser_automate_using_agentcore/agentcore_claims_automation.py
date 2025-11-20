#!/usr/bin/env python3
"""
Claims Automation using Amazon Bedrock AgentCore Browser Tool
"""

import time
from bedrock_agentcore.tools.browser_client import browser_session
from nova_act import NovaAct
from rich.console import Console

console = Console()
NOVA_ACT_API_KEY = '97e6365f-ca2d-44bd-9494-07b1361ee4c9'

# def automate_claims_with_agentcore(base_url="https://YOUR-NGROK-URL.ngrok.io"):
def automate_claims_with_agentcore(base_url="https://fa7602298706.ngrok-free.app"):
    """Automate claims processing using AgentCore Browser Tool + Nova Act"""
    
    console.print("[cyan]🚀 Starting Claims Automation with AgentCore Browser Tool[/cyan]")
    
    try:
        # Step 1: Create AgentCore browser session
        with browser_session('us-west-2') as client:
            console.print("✅ AgentCore browser session created")
            ws_url, headers = client.generate_ws_headers()
            
            # Step 2: Use Nova Act with AgentCore Browser
            with NovaAct(
                cdp_endpoint_url=ws_url,
                cdp_headers=headers,
                nova_act_api_key=NOVA_ACT_API_KEY,
                starting_page=base_url,
                ignore_https_errors=True
            ) as nova_act:
                
                console.print(f"🌐 Connected to claims application at {base_url}")
                
                # Handle ngrok warning page if present
                console.print("[yellow]Checking for ngrok warning page...[/yellow]")
                try:
                    result = nova_act.act("If there is a 'Visit Site' button or 'Continue to site' button, click it to proceed to the actual website")
                    console.print(f"[green]✓ Handled warning page: {result}[/green]")
                    time.sleep(2)
                except:
                    console.print("[yellow]No warning page found, proceeding...[/yellow]")
                
                # Claims processing workflow
                console.print("\n[yellow]Step 1: Switching to Detailed View[/yellow]")
                result = nova_act.act("Click on the Detailed View button")
                console.print(f"[green]✓ {result}[/green]")
                
                # Process claims in a loop
                attempt = 0
                while attempt < 10:  # Safety limit to prevent infinite loop
                    attempt += 1
                    console.print(f"\n[yellow]Looking for unprocessed claims (attempt {attempt})[/yellow]")
                    
                    result = nova_act.act("Look for any claim that has an 'Analyze Complexity' button and click it")
                    
                    if "no claims" in str(result).lower() or "not found" in str(result).lower() or "not available" in str(result).lower():
                        console.print(f"[yellow]No more unprocessed claims found after processing {attempt-1} claims[/yellow]")
                        break
                    
                    console.print(f"[green]✓ Found claim to process: {result}[/green]")
                    
                    # Analyze the claim
                    console.print("[yellow]Starting claim analysis...[/yellow]")
                    time.sleep(3)  # Wait for modal to load
                    
                    result = nova_act.act("Click the green Summarize button")
                    console.print(f"[green]✓ Started summarization: {result}[/green]")
                    
                    time.sleep(8)  # Wait for summarization to complete
                    
                    # Close modal with improved approach
                    console.print("[yellow]Closing analysis modal...[/yellow]")
                    
                    close_attempts = 0
                    close_success = False
                    
                    while close_attempts < 4 and not close_success:
                        try:
                            if close_attempts == 0:
                                result = nova_act.act("Scroll to the bottom of the modal dialog to find a Close button (not the X button) and click it")
                            elif close_attempts == 1:
                                result = nova_act.act("Look for a button labeled 'Close' at the bottom of the modal dialog, ignore the X button at the top")
                            elif close_attempts == 2:
                                result = nova_act.act("Find any button at the bottom of the modal that says Close, Done, or OK and click it")
                            else:
                                result = nova_act.act("Press Escape key to close the modal dialog")
                            
                            console.print(f"[green]✓ Modal closed: {result}[/green]")
                            close_success = True
                            
                        except Exception as close_error:
                            console.print(f"[red]Close attempt {close_attempts + 1} failed: {close_error}[/red]")
                            close_attempts += 1
                            time.sleep(2)
                    
                    if not close_success:
                        console.print("[red]⚠️ Could not close modal, continuing to next claim[/red]")
                    
                    time.sleep(2)
                
                # Return to Queue View
                console.print(f"\n[yellow]Step 3: Returning to Queue View[/yellow]")
                result = nova_act.act("Scroll to the top of the page and click on the blue Queue View button")
                console.print(f"[green]✓ {result}[/green]")
                
                console.print("[bold green]🎉 Claims automation completed![/bold green]")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Automation stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()

def main():
    """Main function to run claims automation"""
    automate_claims_with_agentcore()

if __name__ == "__main__":
    main()
