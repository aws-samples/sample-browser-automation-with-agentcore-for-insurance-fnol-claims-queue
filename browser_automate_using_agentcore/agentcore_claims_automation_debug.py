#!/usr/bin/env python3
"""
Claims Automation with AgentCore Browser Tool - LIVE VIEWER VERSION
Shows actual browser automation happening in real-time!
"""

import time
from bedrock_agentcore.tools.browser_client import browser_session
from nova_act import NovaAct
from rich.console import Console
import webbrowser
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import json
import os
import shutil
import glob
from datetime import datetime

console = Console()
NOVA_ACT_API_KEY = '97e6365f-ca2d-44bd-9494-07b1361ee4c9'

def organize_screenshots(session_logs_dir):
    """Organize screenshots chronologically and open in browser"""
    
    if not session_logs_dir or not os.path.exists(session_logs_dir):
        console.print("[red]❌ No session logs directory found[/red]")
        return None
    
    # Create screenshots folder with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshots_dir = f"/Users/rishikamra/dev/browser_new/browser_automate_using_agentcore/screenshots_{timestamp}"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    # Find all HTML files
    html_files = glob.glob(os.path.join(session_logs_dir, "*.html"))
    
    if not html_files:
        console.print("[red]❌ No HTML files found in session logs[/red]")
        return None
    
    # Sort by creation time
    html_files.sort(key=os.path.getctime)
    
    # Copy files with chronological names
    step_names = [
        "01_check_ngrok_warning",
        "02_click_detailed_view", 
        "03_find_first_claim",
        "04_summarize_first_claim",
        "05_close_first_modal",
        "06_find_second_claim", 
        "07_summarize_second_claim",
        "08_close_second_modal",
        "09_find_third_claim",
        "10_summarize_third_claim", 
        "11_close_third_modal",
        "12_return_to_queue_view"
    ]
    
    copied_files = []
    for i, html_file in enumerate(html_files):
        if i < len(step_names):
            new_name = f"{step_names[i]}.html"
        else:
            new_name = f"{i+1:02d}_automation_step.html"
        
        dest_path = os.path.join(screenshots_dir, new_name)
        shutil.copy2(html_file, dest_path)
        copied_files.append(dest_path)
    
    # Create index HTML
    create_screenshot_index(screenshots_dir, copied_files)
    
    return screenshots_dir

def create_screenshot_index(screenshots_dir, html_files):
    """Create an index HTML to view all screenshots"""
    
    index_content = """
<!DOCTYPE html>
<html>
<head>
    <title>AgentCore Claims Automation Screenshots</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .step { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .step h3 { color: #2c5aa0; margin-top: 0; }
        iframe { width: 100%; height: 600px; border: 1px solid #ccc; }
        .nav { background: #f5f5f5; padding: 10px; margin: 10px 0; }
        .nav a { margin-right: 15px; text-decoration: none; color: #2c5aa0; }
    </style>
</head>
<body>
    <h1>🎬 AgentCore Claims Automation Screenshots</h1>
    <div class="nav">
        <strong>Quick Navigation:</strong>
"""
    
    # Add navigation links
    for i, html_file in enumerate(html_files):
        filename = os.path.basename(html_file)
        step_name = filename.replace('.html', '').replace('_', ' ').title()
        index_content += f'<a href="#{i+1}">Step {i+1}: {step_name}</a>'
    
    index_content += """
    </div>
"""
    
    # Add each screenshot
    for i, html_file in enumerate(html_files):
        filename = os.path.basename(html_file)
        step_name = filename.replace('.html', '').replace('_', ' ').title()
        
        index_content += f"""
    <div class="step" id="{i+1}">
        <h3>Step {i+1}: {step_name}</h3>
        <iframe src="{filename}"></iframe>
    </div>
"""
    
    index_content += """
</body>
</html>
"""
    
    index_path = os.path.join(screenshots_dir, "index.html")
    with open(index_path, 'w') as f:
        f.write(index_content)
    
    return index_path

def automate_claims_with_live_view(base_url="https://fa7602298706.ngrok-free.app"):
    """Automate claims with live viewing capability"""
    
    console.print("[cyan]🚀 Starting Claims Automation - DEBUG MODE[/cyan]")
    console.print("[yellow]📋 Watch detailed progress in this terminal![/yellow]")
    
    try:
        # Create AgentCore browser session
        with browser_session('us-west-2') as client:
            console.print("✅ AgentCore browser session created")
            ws_url, headers = client.generate_ws_headers()
            
            console.print("[cyan]🎬 Starting automation in 3 seconds...[/cyan]")
            time.sleep(3)
            
            # Use Nova Act with AgentCore Browser
            session_logs_dir = None
            with NovaAct(
                cdp_endpoint_url=ws_url,
                cdp_headers=headers,
                nova_act_api_key=NOVA_ACT_API_KEY,
                starting_page=base_url,
                ignore_https_errors=True
            ) as nova_act:
                
                console.print(f"🌐 Connected to claims application at {base_url}")
                
                # Get session logs directory from Nova Act
                if hasattr(nova_act, '_session_logs_directory'):
                    session_logs_dir = nova_act._session_logs_directory
                
                # Handle ngrok warning page if present
                console.print("\n[bold yellow]🔍 STEP 0: Checking for ngrok warning page...[/bold yellow]")
                console.print("[cyan]The browser is checking if there's a warning page to dismiss[/cyan]")
                try:
                    result = nova_act.act("If there is a 'Visit Site' button or 'Continue to site' button, click it to proceed to the actual website")
                    console.print(f"[green]✓ Result: {result}[/green]")
                    time.sleep(3)
                except:
                    console.print("[yellow]No warning page found, proceeding...[/yellow]")
                
                # Claims processing workflow with detailed commentary
                console.print("\n[bold yellow]📋 STEP 1: Switching to Detailed View[/bold yellow]")
                console.print("[cyan]The browser is looking for and clicking the 'Detailed View' button[/cyan]")
                result = nova_act.act("Click on the Detailed View button")
                console.print(f"[green]✓ Switched to Detailed View: {result}[/green]")
                time.sleep(4)
                
                # Process claims in a loop with detailed commentary
                attempt = 0
                while attempt < 10:  # Safety limit to prevent infinite loop
                    attempt += 1
                    console.print(f"\n[bold yellow]🎯 STEP 2.{attempt}: Processing Claim #{attempt}[/bold yellow]")
                    console.print("[cyan]The browser is scanning for claims with 'Analyze Complexity' buttons[/cyan]")
                    
                    result = nova_act.act("Look for any claim that has an 'Analyze Complexity' button and click it")
                    
                    if "no claims" in str(result).lower() or "not found" in str(result).lower() or "not available" in str(result).lower():
                        console.print(f"[yellow]✓ No more unprocessed claims found after processing {attempt-1} claims[/yellow]")
                        break
                    
                    console.print(f"[green]✓ Found and clicked claim: {result}[/green]")
                    console.print("[cyan]📊 Modal dialog opened - waiting for it to fully load...[/cyan]")
                    time.sleep(3)
                    
                    # Analyze the claim
                    console.print("[cyan]The browser is looking for and clicking the green 'Summarize' button[/cyan]")
                    time.sleep(2)
                    
                    result = nova_act.act("Click the green Summarize button")
                    console.print(f"[green]✓ Started analysis: {result}[/green]")
                    
                    console.print("[cyan]⏳ Waiting 8 seconds for AI analysis to complete...[/cyan]")
                    time.sleep(8)
                    
                    # Close modal
                    console.print("[cyan]The browser is scrolling down to find the proper 'Close' button (not the X)[/cyan]")
                    
                    try:
                        result = nova_act.act("Scroll to the bottom of the modal dialog to find a Close button (not the X button) and click it")
                        console.print(f"[green]✓ Modal closed successfully: {result}[/green]")
                        time.sleep(3)
                    except Exception as close_error:
                        console.print(f"[red]⚠️ Could not close modal: {close_error}[/red]")
                    
                    console.print(f"[green]✅ Claim #{attempt+1} processing completed![/green]")
                    time.sleep(2)
                
                # Return to Queue View
                console.print(f"\n[bold yellow]🔄 STEP 3: Returning to Queue View[/bold yellow]")
                console.print("[cyan]The browser is scrolling to top and clicking the 'Queue View' button[/cyan]")
                result = nova_act.act("Scroll to the top of the page and click on the blue Queue View button")
                console.print(f"[green]✓ Returned to Queue View: {result}[/green]")
                time.sleep(3)
                
                console.print("\n[bold green]🎉 AUTOMATION COMPLETED SUCCESSFULLY![/bold green]")
            
            # Organize screenshots after automation completes
            console.print("\n[cyan]📸 Organizing screenshots...[/cyan]")
            screenshots_dir = organize_screenshots(session_logs_dir)
            
            if screenshots_dir:
                console.print(f"[green]✅ Screenshots organized in: {screenshots_dir}[/green]")
                
                # Open index in browser
                index_path = os.path.join(screenshots_dir, "index.html")
                if os.path.exists(index_path):
                    console.print("[cyan]🌐 Opening screenshot gallery in browser...[/cyan]")
                    webbrowser.open(f"file://{index_path}")
                    console.print(f"[yellow]📁 Screenshots saved to: {screenshots_dir}[/yellow]")
                else:
                    console.print("[yellow]📁 Screenshots copied but no index created[/yellow]")
            else:
                console.print("[red]❌ Could not organize screenshots[/red]")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Automation stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()

def main():
    """Main function to run debug claims automation"""
    console.print("[bold cyan]🐛 DEBUG MODE: Claims Automation[/bold cyan]")
    console.print("[yellow]This will show detailed progress and organize screenshots automatically![/yellow]")
    console.print("[yellow]After completion, it will open a browser gallery of all screenshots![/yellow]\n")
    
    automate_claims_with_live_view()

if __name__ == "__main__":
    main()
