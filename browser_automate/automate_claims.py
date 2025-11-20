#!/usr/bin/env python3
"""
Complete Claims Automation - Handles all scenarios in one script
"""

import time
from nova_act import NovaAct
from rich.console import Console

console = Console()
NOVA_ACT_API_KEY = '97e6365f-ca2d-44bd-9494-07b1361ee4c9'

def automate_claims():
    """Complete claims automation with all features"""
    
    console.print("[cyan]🚀 Starting Complete Claims Automation[/cyan]")
    console.print("[yellow]Handles any number of claims with smart scrolling[/yellow]")
    
    try:
        with NovaAct(
            nova_act_api_key=NOVA_ACT_API_KEY,
            starting_page="http://localhost:3000",
            ignore_https_errors=True
        ) as nova_act:
            
            console.print("🌐 Connected to claims application")
            
            # Step 1: Switch to Detailed View
            console.print("[yellow]Step 1: Switching to Detailed View[/yellow]")
            result = nova_act.act("Click on the Detailed View button")
            console.print(f"[green]✓ {result}[/green]")
            time.sleep(3)
            
            # Step 2: Process all claims dynamically
            claims_processed = 0
            max_attempts = 20  # Safety limit
            
            while claims_processed < max_attempts:
                console.print(f"\n[blue]Looking for unprocessed claims (attempt {claims_processed + 1})[/blue]")
                
                try:
                    # Find and click an "Analyze Complexity" button
                    result = nova_act.act("Look for any claim that has an 'Analyze Complexity' button and click it")
                    console.print(f"[green]✓ Found claim to process: {result}[/green]")
                    time.sleep(2)
                    
                    # Click Summarize button
                    console.print("[yellow]Starting claim analysis...[/yellow]")
                    result = nova_act.act("Click the green Summarize button")
                    console.print(f"[green]✓ Started summarization: {result}[/green]")
                    time.sleep(8)  # Wait for summarization to complete
                    
                    # Smart Close button handling for modal dialog
                    console.print("[yellow]Looking for Close button in modal dialog...[/yellow]")
                    
                    close_attempts = 0
                    close_success = False
                    
                    while close_attempts < 4 and not close_success:
                        try:
                            if close_attempts == 0:
                                result = nova_act.act("Scroll down to the bottom of the modal dialog to find a Close button (not the X button) and click it")
                            elif close_attempts == 1:
                                result = nova_act.act("Look for a button labeled 'Close' at the bottom of the modal dialog, ignore the X button at the top")
                            elif close_attempts == 2:
                                result = nova_act.act("Find any button at the bottom of the modal that says Close, Done, or OK and click it")
                            else:
                                result = nova_act.act("Press Escape key to close the modal dialog")
                            
                            console.print(f"[green]✓ Modal closed: {result}[/green]")
                            close_success = True
                            
                        except Exception:
                            close_attempts += 1
                            console.print(f"[yellow]Close attempt {close_attempts}/4, trying different approach...[/yellow]")
                            time.sleep(1)
                    
                    if not close_success:
                        console.print("[red]⚠️ Could not find Close button, continuing to next claim[/red]")
                    
                    time.sleep(2)
                    claims_processed += 1
                    console.print(f"[green]✅ Claim {claims_processed} processed successfully[/green]")
                    
                except Exception as e:
                    console.print(f"[yellow]No more unprocessed claims found[/yellow]")
                    break
            
            # Step 3: Return to Queue View
            console.print(f"\n[yellow]Step 3: Returning to Queue View[/yellow]")
            result = nova_act.act("Scroll to the top of the page and click on the blue Queue View button")
            console.print(f"[green]✓ {result}[/green]")
            
            console.print(f"[bold green]🎉 Processed {claims_processed} claims successfully![/bold green]")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")

if __name__ == "__main__":
    automate_claims()
