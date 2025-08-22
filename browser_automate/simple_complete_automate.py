#!/usr/bin/env python3
"""
Simple Complete FNOL Claims Processing Automation
Processes all claims by scrolling through the page systematically
"""

import time
from nova_act import NovaAct

def main():
    print("🤖 Simple Complete FNOL Claims Processing Automation")
    print("Will process ALL claims by scrolling through the page")
    print()
    
    base_url = "http://localhost:8000"
    
    try:
        with NovaAct(
            starting_page=base_url,
            ignore_https_errors=True,
            headless=False
        ) as act:
            print("🌐 Browser opened, navigating to FNOL application...")
            time.sleep(2)
            
            # Switch to detailed view
            print("📋 Switching to detailed view...")
            act.act("Look for a button labeled 'Detailed View' and click it")
            time.sleep(2)
            
            # Process claims in a loop with increased attempts
            max_attempts = 15  # Increased to handle all 7 claims
            processed_claims = 0
            
            for attempt in range(1, max_attempts + 1):
                print(f"🔄 Attempt {attempt}: Looking for red 'Analyze Complexity' buttons...")
                
                # Step 1: Find and click any red 'Analyze Complexity' button
                # Include scrolling in the search command
                result = act.act(
                    "Look at all the claim cards on the page. If you don't see any red 'Analyze Complexity' buttons "
                    "in the current view, scroll down to see more claims. "
                    "Find any button that says 'Analyze Complexity' and is red in color. "
                    "If you find one, click it and say 'CLICKED_ANALYZE_BUTTON'. "
                    "If no red 'Analyze Complexity' buttons are found anywhere on the page, say 'NO_BUTTONS_FOUND'."
                )
                
                print(f"🔍 Step 1 result: {result}")
                
                # Check the response
                result_text = ""
                if hasattr(result, 'response') and result.response:
                    result_text = str(result.response).upper()
                else:
                    # Look for evidence of clicking
                    full_result = str(result).upper()
                    if "AGENTCLICK" in full_result:
                        result_text = "CLICKED_ANALYZE_BUTTON"
                    else:
                        result_text = "NO_BUTTONS_FOUND"
                
                print(f"🔍 Interpreted result: {result_text}")
                
                # Check if no buttons were found
                if "NO_BUTTONS_FOUND" in result_text:
                    print("✅ No more red 'Analyze Complexity' buttons found. All claims processed!")
                    break
                
                if "CLICKED_ANALYZE_BUTTON" not in result_text:
                    print(f"⚠️ Unexpected result in attempt {attempt}: {result_text}")
                    continue
                
                print("🎯 Successfully clicked 'Analyze Complexity' button!")
                processed_claims += 1
                
                # Step 2: Wait for modal to appear
                print("⏳ Waiting for modal dialog to appear...")
                time.sleep(3)
                
                # Step 3: Click Summarize button
                print("🟢 Looking for green 'Summarize' button in modal dialog...")
                summarize_result = act.act(
                    "Look for a modal dialog with claim details. "
                    "In this dialog, find a green button that says 'Summarize' and click it. "
                    "If the dialog is long, scroll down to find the Summarize button at the bottom."
                )
                print(f"🟢 Summarize button result: {summarize_result}")
                
                # Step 4: Wait for analysis to complete
                print("⏳ Waiting for AI analysis to complete...")
                time.sleep(6)
                
                # Step 5: Close the modal
                print("❌ Looking for 'Close' button to close the modal...")
                close_result = act.act(
                    "In the modal dialog, look for a button that says 'Close' (not 'Cancel' or 'X'). "
                    "The Close button should be at the bottom of the dialog after analysis is complete. "
                    "If you can't see the Close button, scroll down within the modal dialog. "
                    "Once you find the 'Close' button, click it to close the modal. "
                    "Say 'CLICKED_CLOSE' when you click it, or 'CLOSE_NOT_FOUND' if you can't find it."
                )
                
                print(f"❌ Close result: {close_result}")
                
                # Check if close was successful
                close_text = ""
                if hasattr(close_result, 'response') and close_result.response:
                    close_text = str(close_result.response).upper()
                else:
                    full_close_result = str(close_result).upper()
                    if "CLICKED_CLOSE" in full_close_result:
                        close_text = "CLICKED_CLOSE"
                
                if "CLICKED_CLOSE" in close_text:
                    print("✅ Successfully clicked Close button!")
                else:
                    print("⚠️ Had trouble closing modal, but continuing...")
                
                print(f"✅ Completed processing for attempt {attempt}")
                
                # Brief pause between attempts
                time.sleep(2)
                print()  # Empty line for readability
            
            # Return to queue view
            print("🔄 Going back to Queue view...")
            act.act("Look for a button labeled 'Queue View' and click it")
            time.sleep(2)
            print("✅ Returned to Queue view")
            
            print()
            print("🎉 Automation completed!")
            print(f"📊 Total claims processed: {processed_claims}")
            print("📊 Check the FNOL application to see the results of the claim analyses.")
            
    except Exception as e:
        print(f"❌ Error during automation: {e}")
        print("🔍 Check the Nova Act logs for more details")

if __name__ == "__main__":
    main()
