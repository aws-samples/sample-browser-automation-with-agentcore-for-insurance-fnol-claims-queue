#!/usr/bin/env python3
"""
Simple test to verify AgentCore Browser connection
"""

import time
from bedrock_agentcore.tools.browser_client import browser_session
from rich.console import Console

console = Console()

def test_agentcore_connection():
    """Test basic AgentCore Browser connection"""
    
    console.print("[cyan]🧪 Testing AgentCore Browser Connection[/cyan]")
    
    try:
        # Create AgentCore browser session
        with browser_session('us-west-2') as client:
            console.print("✅ AgentCore browser session created")
            ws_url, headers = client.generate_ws_headers()
            console.print(f"✅ WebSocket URL: {ws_url}")
            console.print(f"✅ Headers generated: {len(headers)} headers")
            
            console.print("[green]🎉 AgentCore Browser connection successful![/green]")
            console.print("[yellow]Now try connecting Nova Act to this endpoint...[/yellow]")
            
            # Keep session alive for a moment
            time.sleep(5)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agentcore_connection()
