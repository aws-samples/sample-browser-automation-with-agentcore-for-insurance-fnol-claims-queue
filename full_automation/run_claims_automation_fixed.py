#!/usr/bin/env python3
import os
import sys
import time
import argparse
from datetime import datetime
from rich.console import Console
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import urllib.parse
from nova_act import NovaAct
from nova_act.types.act_errors import ActInvalidModelGenerationError


console = Console()
NOVA_ACT_API_KEY = os.getenv("NOVA_ACT_API_KEY") or "abcd-efgh-ijkl-1234-5678"

def text(resp):
    if hasattr(resp, "response") and resp.response:
        return str(resp.response)
    return str(resp)

STRICT_EVIDENCE_PROMPT = """
You are looking ONLY at the CURRENT SCREEN. DO NOT SCROLL. DO NOT MOVE THE PAGE.

CRITICAL INSTRUCTION: Your job is to find unprocessed evidence and click its button to start processing.

IMPORTANT: When you click a button and a modal opens, that is SUCCESS. 
DO NOT CLOSE THE MODAL. DO NOT CLICK CANCEL. 
When a modal opens, respond EXACTLY with: 
RESULT: MODAL_OPENED

Look for these EXACT text patterns CURRENTLY VISIBLE on screen:
- "Images (number)" 
- "Videos (number)"  
- "Audio (number)"

For EACH one you can see RIGHT NOW, look IMMEDIATELY to the right of the text for the ✔ CHECKMARK SYMBOL.

+ IMPORTANT VISUAL CLARIFICATION ABOUT ✔:
- The ✔ may appear inside a small green box or badge.
- The ✔ may not be immediately adjacent to the text but still on the SAME ROW.
- If a ✔ icon is visible on the same row as the label, it COUNTS as PROCESSED.

PROCESSED = you can ACTUALLY SEE a ✔ checkmark symbol directly after the text:
- "Images (4) ✔" ← you see the ✔ symbol (DO NOT CLICK - already processed)
- "Videos (2) ✔" ← you see the ✔ symbol (DO NOT CLICK - already processed)
- "Audio (0) ✔" ← you see the ✔ symbol (DO NOT CLICK - already processed)

UNPROCESSED = you do NOT see a ✔ checkmark symbol after the text:
- "Images (4)" ← NO ✔ symbol visible (CLICK ITS BUTTON to process it)
- "Videos (2)" ← NO ✔ symbol visible (CLICK ITS BUTTON to process it)
- "Audio (0)" ← NO ✔ symbol visible (CLICK ITS BUTTON to process it)

+ IMPORTANT ABOUT PLACEHOLDER TEXT:
- If you see placeholder text such as:
  "Analysis tags will appear here..."
  this means the evidence is NOT processed.
- Treat this as UNPROCESSED even if the section has a border or button.

DO NOT SCROLL. DO NOT MOVE THE PAGE. Only work with what is CURRENTLY VISIBLE.

If you see "Audio (2)" text but cannot see if it has a checkmark because it's cut off, treat it as UNPROCESSED and click its button.

STEP-BY-STEP PROCESS:
1. Look at ONLY what is visible RIGHT NOW on screen
2. Find ALL "Images (number)", "Videos (number)", "Audio (number)" text you can see
3. For EACH one, check if you can see ✔ symbol directly to the right
4. If ANY is missing ✔ or you cannot see the full text clearly, find its "Analyze" button and CLICK it
5. If ALL visible ones have clear ✔ symbols, respond: RESULT: NONE

DO NOT SCROLL. DO NOT MOVE. Only work with current viewport.

If you find ANY text missing the ✔ symbol or partially visible:
- Click its "Analyze Images", "Analyze Videos", or "Analyze Audio" button
- If modal opens: RESULT: MODAL_OPENED
- If no modal: RESULT: NO_MODAL

If ALL visible text has clear ✔ symbols: RESULT: NONE

Your response must be EXACTLY one of:
RESULT: NONE
RESULT: NO_MODAL  
RESULT: MODAL_OPENED

DO NOT SCROLL. DO NOT ASSUME. DO NOT INVENT CHECKMARKS.  DO NOT CLOSE MODALS.
Only count checkmarks that are ACTUALLY VISIBLE on screen.

Modal opening means the button worked successfully.
END OF INSTRUCTIONS. Do not add any additional formatting or schema requirements.

"""
def act_with_retry(nova, prompt, retries=3, delay=1):
    for attempt in range(1, retries + 1):
        try:
            return nova.act_get(prompt)
        except Exception as e:
            if attempt == retries:
                raise
            console.print(
                f"[yellow]⚠️ nova.act_get failed (attempt {attempt}/{retries}), retrying...[/yellow]"
            )
            time.sleep(delay)

    

def click_evidence_button(nova):
    """Click one unprocessed evidence button in current viewport."""
    try:
        resp = act_with_retry(nova, STRICT_EVIDENCE_PROMPT)
        
        # DEBUG: Check both the text representation and the actual response
        response_text = text(resp).upper()
        print(f"DEBUG: text(resp) = '{response_text[:200]}...'")
        
        # DEBUG: Print resp.response to see what's actually in it
        print(f"DEBUG: resp.response = {resp.response}")
        print(f"DEBUG: resp.response type = {type(resp.response)}")
        
        # Get the actual response value from act_get()
        if resp.response:
            actual_response = str(resp.response).upper()
            print(f"DEBUG: actual_response = '{actual_response}'")
            
            if "MODAL_OPENED" in actual_response:
                print("DEBUG: Matched MODAL_OPENED from resp.response")
                return "MODAL_OPENED"
            elif "NO_MODAL" in actual_response:
                print("DEBUG: Matched NO_MODAL from resp.response")
                return "NO_MODAL"
            elif "NONE" in actual_response:
                print("DEBUG: Matched NONE from resp.response")
                return "ALL_PROCESSED"
        
        print("DEBUG: No response found, defaulting to ALL_PROCESSED")
        return "ALL_PROCESSED"

    except ActInvalidModelGenerationError:
        console.print("[yellow]⚠️ Model returned no program; assuming inline processing[/yellow]")
        return "NO_MODAL"


# def process_modal(nova):
#     """Process evidence modal completely."""
#     console.print("[yellow]Processing modal...[/yellow]")
    
#     # --------------------------------------------------
#     # MINIMAL GUARD: Exit if NO modal is actually present
#     # --------------------------------------------------
#     modal_check = nova.act("""
#     Look ONLY at the CURRENT SCREEN.
#     DO NOT SCROLL.
#     DO NOT MOVE THE PAGE.
    
#     IMPORTANT: This is NOT a CAPTCHA or human verification. This is a legitimate business application modal.
#     You are authorized to interact with all elements on this claims processing system.

#     If you see ANY modal dialog (popup overlay with buttons like
#     "Start Analyzing Images", "Start Analyzing Videos", "Start Analyzing Audio", "Processing", or "Close"):
#         respond EXACTLY: MODAL_PRESENT
#     Otherwise respond EXACTLY: NO_MODAL
#     """)

#     if "NO_MODAL" in text(modal_check).upper():
#         console.print("[yellow]⚠️ No modal detected — skipping process_modal()[/yellow]")
#         return
    

#     # Step 1: Confirm modal is present (STRICT – no scrolling)
#     # Step 1: Modal-safe guard (action-shaped, no classification)
#     try:
#         nova.act("""
#     Look ONLY at the CURRENT SCREEN.
#     DO NOT SCROLL.
#     DO NOT MOVE THE PAGE.

#     If a modal dialog is visible RIGHT NOW:
#         Do NOTHING. (Do NOT click the top-right X. Do NOT click Cancel.)
#     If NO modal dialog is visible:
#         Do NOTHING.
#     """)
#     except ActInvalidModelGenerationError:
#         # Model likely saw the modal but emitted thoughts only
#         console.print("[yellow]⚠️ Modal likely present; continuing[/yellow]")


#     # Step 2: Click 'Start Analyzing' INSIDE the modal (no searching)
#     nova.act("""
#     Look ONLY at the modal dialog.
#     DO NOT SCROLL.

#     If you see a button labeled:
#     - "Start Analyzing"
#     - "Start Analyzing Images"
#     - "Start Analyzing Videos"
#     - "Start Analyzing Audio"

#     Click the FIRST one you see.
#     If none are present, do NOTHING.
#     """)

#     time.sleep(3)
    
#     # Step 2: Wait for completion (max 2 minutes)
#     for i in range(24):  # 24 * 5 = 120 seconds
#         time.sleep(5)
        
#         status = nova.act("""
#         IGNORE the background page. Look ONLY at the modal popup window.

#         In the modal:
#         If you see a "Close" button, respond: "READY_TO_CLOSE"

#         If you see ANY text indicating analysis is in progress
#         (e.g. "Analyzing", "Analyzing videos", "Analyzing audio", "Processing"):
#         respond: "PROCESSING"

#         If you see a button labeled "Start Analyzing", "Start Analyzing Audio",
#         "Start Analyzing Images", or "Start Analyzing Videos":
#         respond "START_AVAILABLE"

#         Otherwise respond: "UNKNOWN"

#         DO NOT look at the background page. Only look at the modal.
#         """)

#         status_text = text(status).upper()

#         if "START_AVAILABLE" in status_text:
#             nova.act("""
#             Look ONLY at the modal dialog.
#             Click the "Start Analyzing" button.
#             """)
#             time.sleep(3)
#             continue
        
#         if "READY_TO_CLOSE" in text(status).upper() or "CLOSE" in text(status).upper():
#             break
    
#     # Step 3: Close modal
#     nova.act('Click the "Close" button in the modal to close it.')
#     time.sleep(3)  # Give extra time for page to update after modal closes
    
#     # Step 4: Prevent unwanted scrolling
#     nova.act('The modal is closed. DO NOT SCROLL. Stay in the current viewport.')
#     time.sleep(1)
    
#     console.print("[green]Modal processed[/green]")

def process_modal(nova):
    """Process evidence modal completely."""
    console.print("[yellow]Processing evidence modal...[/yellow]")
    
    # Step 1: Try to click modal button (defines modal by its interactive elements)
    try:
        nova.act('''
        Look ONLY at the CURRENT SCREEN.
        DO NOT SCROLL. DO NOT MOVE THE PAGE. DO NOT SCROLL DOWN OR UP.
        
        If you see ANY modal dialog (popup overlay with buttons like
        "Start Analyzing Images", "Start Analyzing Videos", "Start Analyzing Audio", "Processing", or "Close"):
        
        Then click ONLY ONE of these buttons in the modal:
        - "Start Analyzing Images" button
        - "Start Analyzing Videos" button  
        - "Start Analyzing Audio" button
        
        Click whichever one of these three buttons you can see in the modal.
        
        DO NOT SCROLL. DO NOT MOVE THE PAGE.
        ''')
        console.print("[green]Evidence modal confirmed - Start Analyzing button clicked[/green]")
    except:
        console.print("[yellow]⚠️ No evidence modal detected — skipping process_modal()[/yellow]")
        return
    
    time.sleep(3)
    
    # Step 2: Wait for Close button to appear (processing takes time)
    console.print("[cyan]Waiting for processing to complete and Close button to appear...[/cyan]")
    
    for i in range(10):  # 10 * 5 = 50 seconds max
        time.sleep(5)
        
        try:
            nova.act('''
            DO NOT SCROLL. DO NOT MOVE THE PAGE.
            
            Click the button that has the text "Close" written on it.
            DO NOT click the X symbol in the top-right corner.
            DO NOT click any X buttons.
            DO NOT click the button that says "Cancel".
            Only click the rectangular button that says "Close".
            
            DO NOT SCROLL.
            ''')
            console.print("[green]Processing complete - Close button found and clicked[/green]")
            break
        except:
            console.print(f"[cyan]Close button not ready yet... waiting (attempt {i+1}/8)[/cyan]")
            continue
    
    # Step 3: Prevent unwanted scrolling
    nova.act('''
    DO NOT SCROLL. YOU MUST STAY in the current viewport.
    Stay on this page.
    ''')
    time.sleep(2)
    
    console.print("[green]Evidence modal processed[/green]")

def process_complexity_modal(nova):
    """Process complexity analysis modal completely."""
    console.print("[yellow]Processing complexity modal...[/yellow]")
    
    # Step 1: Click Summarize button
    try:
        nova.act('''
        Look ONLY at the CURRENT SCREEN.
        DO NOT SCROLL. DO NOT MOVE THE PAGE.
        
        If you see a modal dialog for complexity analysis:
        Click the green "Summarize" button in the modal.
        
        DO NOT SCROLL. DO NOT MOVE THE PAGE.
        ''')
        console.print("[green]Complexity modal confirmed - Summarize button clicked[/green]")
    except:
        console.print("[yellow]⚠️ No complexity modal detected — skipping process_complexity_modal()[/yellow]")
        return
    
    # Step 2: Wait for summarization to complete
    console.print("[cyan]Waiting 8 seconds for summarization to complete...[/cyan]")
    time.sleep(8)
    
    # Step 3: Smart Close button handling with multiple attempts
    console.print("[cyan]Looking for Close button in modal dialog...[/cyan]")
    
    close_attempts = 0
    close_success = False
    
    while close_attempts < 4 and not close_success:
        try:
            if close_attempts == 0:
                nova.act("Scroll down to the bottom of the modal dialog to find a Close button (not the X button) and click it")
            elif close_attempts == 1:
                nova.act("Look for a button labeled 'Close' at the bottom of the modal dialog, ignore the X button at the top")
            elif close_attempts == 2:
                nova.act("Find any button at the bottom of the modal that says Close, Done, or OK and click it")
            else:
                nova.act("Press Escape key to close the modal dialog")
            
            console.print(f"[green]✓ Modal closed successfully[/green]")
            close_success = True
            
        except Exception:
            close_attempts += 1
            console.print(f"[yellow]Close attempt {close_attempts}/4, trying different approach...[/yellow]")
            time.sleep(1)
    
    if not close_success:
        console.print("[red]⚠️ Could not find Close button, continuing anyway[/red]")
    
    time.sleep(2)
    console.print("[green]Complexity modal processed[/green]")

def has_more_content_below(nova):
    """Check if more content exists below current viewport."""
    try:
        resp = nova.act_get("""
DO NOT SCROLL. DO NOT MOVE THE PAGE.

Look at the CURRENT screen only.

Check BOTH indicators:
1. Scroll bar: Look at the scroll bar on the right side - is it at the very bottom?
2. Content: Is content clearly cut off and continues below the visible area?

- If scroll bar is at bottom AND no content is cut off: respond "AT_BOTTOM"
- If scroll bar shows more scrolling possible OR content is cut off: respond "MORE_BELOW"

Use both the scroll bar position and content visibility to decide.
""")
        
        # DEBUG: Print response details
        print(f"DEBUG has_more_content_below: resp = {resp}")
        print(f"DEBUG has_more_content_below: resp.response = {resp.response}")
        print(f"DEBUG has_more_content_below: resp.response type = {type(resp.response)}")
        
        if resp.response:
            response_text = str(resp.response).upper()
            print(f"DEBUG has_more_content_below: response_text = '{response_text}'")
            result = "MORE_BELOW" in response_text or "MORE" in response_text
            print(f"DEBUG has_more_content_below: returning {result}")
            return result
        
        print("DEBUG has_more_content_below: No response, returning False")
        return False
        
    except Exception as e:
        print(f"DEBUG has_more_content_below: Exception = {e}")
        print(f"DEBUG has_more_content_below: Exception type = {type(e)}")
        return False  # Assume at bottom if error

def scroll_down_one_section(nova):
    """Scroll down just enough to reveal the next section."""
    nova.act("Scroll down one screen to reveal more content.")
    time.sleep(1)

def run_evidence_phase(nova):
    """Process all evidence buttons with unidirectional scrolling - configurable passes."""
    console.print("[bold cyan]PHASE 1: Evidence Processing[/bold cyan]")
    
    # TODO: Change to [1, 2] for two-pass evidence system for better coverage
    for pass_num in [1]:  # Single pass for now, can be changed to [1, 2] for two passes
        total_passes = len([1])  # Update this when changing pass configuration above
        console.print(f"[bold yellow]Evidence Pass {pass_num}/{total_passes}[/bold yellow]")
        
        # Start at top for each pass
        nova.act("Scroll to the top of the page.")
        time.sleep(2)
        
        scroll_attempts = 0
        max_scroll_attempts = 10  # Prevent infinite loops
        
        while scroll_attempts < max_scroll_attempts:
            # Process ALL unprocessed sections in current viewport
            viewport_attempts = 0
            max_viewport_attempts = 5  # Prevent infinite loops in same viewport
            
            while viewport_attempts < max_viewport_attempts:
                console.print(f"[cyan]Pass {pass_num} - Checking viewport for unprocessed evidence (attempt {viewport_attempts + 1})...[/cyan]")
                result = click_evidence_button(nova)
                
                if result == "MODAL_OPENED":
                    console.print("[green]Modal opened! Processing...[/green]")
                    process_modal(nova)
                    console.print("[yellow]Modal closed. Re-checking same viewport for more unprocessed sections...[/yellow]")
                    viewport_attempts = 0  # Reset counter after successful modal processing
                    continue  # Re-check same viewport for more unprocessed sections
                elif result == "NO_MODAL":
                    console.print("[yellow]Button clicked but no modal - continuing...[/yellow]")
                    viewport_attempts += 1
                    continue  # Try next unprocessed section in viewport
                else:  # ALL_PROCESSED
                    console.print("[green]All sections in current viewport are processed[/green]")
                    break  # Move to scrolling
            
            if viewport_attempts >= max_viewport_attempts:
                console.print("[yellow]Max attempts reached in viewport, moving to next...[/yellow]")
            
            # Check if more content below
            if has_more_content_below(nova):
                console.print(f"[cyan]Scrolling to next viewport... (scroll attempt {scroll_attempts + 1}/{max_scroll_attempts})[/cyan]")
                scroll_down_one_section(nova)
                scroll_attempts += 1
                print(f"DEBUG scroll_attempts: Incremented to {scroll_attempts}/{max_scroll_attempts}")
            else:
                console.print(f"[green]Reached bottom - Evidence pass {pass_num} complete[/green]")
                print(f"DEBUG scroll_attempts: Exiting at bottom with {scroll_attempts} scroll attempts used")
                break
        
        if scroll_attempts >= max_scroll_attempts:
            console.print(f"[yellow]Max scroll attempts reached ({scroll_attempts}/{max_scroll_attempts}) - Evidence pass {pass_num} complete[/yellow]")
            print(f"DEBUG scroll_attempts: Hit maximum limit of {max_scroll_attempts} attempts")
    
    console.print("[bold green]All evidence processing complete (1 pass done)[/bold green]")

def click_complexity_button(nova):
    """Click one Analyze Complexity button."""
    resp = nova.act_get("""
Look for a button with EXACT text: "Analyze Complexity".

If you find it:
    CLICK IT.
    If a modal opens: return("RESULT: MODAL_OPENED")
    If no modal opens: return("RESULT: NO_MODAL")

If no "Analyze Complexity" button exists: return("RESULT: NONE")
""")
    
    if resp.response:
        response = str(resp.response).upper()
        if "RESULT: MODAL_OPENED" in response or "MODAL_OPENED" in response:
            return "MODAL_OPENED"
        elif "RESULT: NO_MODAL" in response or "NO_MODAL" in response:
            return "NO_MODAL"
        else:
            return "NONE"
    return "NONE"

def run_complexity_phase(nova):
    """Process all Analyze Complexity buttons."""
    console.print("[bold cyan]PHASE 2: Complexity Processing[/bold cyan]")
    
    nova.act("Scroll to the very top of the page.")
    time.sleep(2)
    
    scroll_attempts = 0
    max_scroll_attempts = 10  # Prevent infinite loops
    
    while scroll_attempts < max_scroll_attempts:
        result = click_complexity_button(nova)
        
        if result == "MODAL_OPENED":
            console.print("[green]Complexity modal opened! Processing...[/green]")
            process_complexity_modal(nova)
            continue
        elif result == "NO_MODAL":
            console.print("[yellow]Complexity button clicked but no modal[/yellow]")
            continue
        else:  # NONE
            # No complexity buttons in viewport, try scrolling
            if has_more_content_below(nova):
                console.print(f"[cyan]Scrolling to find more complexity buttons... (scroll attempt {scroll_attempts + 1}/{max_scroll_attempts})[/cyan]")
                scroll_down_one_section(nova)
                scroll_attempts += 1
                print(f"DEBUG complexity scroll_attempts: Incremented to {scroll_attempts}/{max_scroll_attempts}")
            else:
                console.print("[green]All complexity buttons processed[/green]")
                print(f"DEBUG complexity scroll_attempts: Exiting at bottom with {scroll_attempts} scroll attempts used")
                break
    
    if scroll_attempts >= max_scroll_attempts:
        console.print(f"[yellow]Max scroll attempts reached ({scroll_attempts}/{max_scroll_attempts}) - Complexity phase complete[/yellow]")
        print(f"DEBUG complexity scroll_attempts: Hit maximum limit of {max_scroll_attempts} attempts")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_url", default="https://dsjo0fgkeahyy.cloudfront.net/")
    args = parser.parse_args()

    if not os.path.exists("browser_id.txt"):
        console.print("[red]Missing browser_id.txt[/red]")
        sys.exit(1)

    browser_id = open("browser_id.txt").read().strip()
    session = boto3.Session()
    region = "us-west-2"
    agentcore = session.client("bedrock-agentcore", region_name=region)

    session_id = agentcore.start_browser_session(
        browserIdentifier=browser_id,
        name=f"claims-fixed-{int(time.time())}",
        sessionTimeoutSeconds=7200, #2 hours
    )["sessionId"]

    details = agentcore.get_browser_session(
        browserIdentifier=browser_id,
        sessionId=session_id,
    )
    ws_url = details["streams"]["automationStream"]["streamEndpoint"]

    creds = session.get_credentials()
    parsed = urllib.parse.urlparse(ws_url)
    req = AWSRequest(method="GET", url=ws_url, headers={"Host": parsed.netloc})
    SigV4Auth(creds, "bedrock-agentcore", region).add_auth(req)
    headers = dict(req.headers)

    logs_dir = f"screenshots/session_{datetime.now().strftime('%Y%m%d_%H%M%S')}/{session_id}"
    os.makedirs(logs_dir, exist_ok=True)

    nova_cfg = {
        "cdp_endpoint_url": ws_url,
        "cdp_headers": headers,
        "nova_act_api_key": NOVA_ACT_API_KEY,
        "starting_page": args.base_url,
        "logs_directory": logs_dir,
        "ignore_https_errors": True,
    }

    try:
        with NovaAct(**nova_cfg) as nova:
            console.print("[bold cyan]Starting Fixed Claims Automation[/bold cyan]")
            
            # Switch to detailed view
            nova.act('If you see a "Detailed View" button, click it.')
            time.sleep(2)
            
            # Run evidence processing (2 passes)
            run_evidence_phase(nova)
            
            # Run complexity processing  
            run_complexity_phase(nova)
            
            console.print("[bold green]All claim analyses completed successfully[/bold green]")

    finally:
        try:
            agentcore.stop_browser_session(
                browserIdentifier=browser_id, sessionId=session_id
            )
        except:
            pass

if __name__ == "__main__":
    main()
