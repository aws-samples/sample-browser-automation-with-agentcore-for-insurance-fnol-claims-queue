#!/usr/bin/env python3
"""
Fixed Interactive Automation Recorder with proper step limits
"""

from nova_act import NovaAct
from rich.console import Console
from rich.prompt import Prompt
import json
import time

console = Console()
NOVA_ACT_API_KEY = '97e6365f-ca2d-44bd-9494-07b1361ee4c9'

def live_recording_mode_fixed():
    """Live recording mode with proper step management"""
    
    console.print("[cyan]🔴 Live Recording Mode (Fixed)[/cyan]")
    console.print("[yellow]Give me SHORT, SIMPLE instructions one at a time![/yellow]")
    console.print("[red]❌ Don't say: 'Process all claims and do everything'[/red]")
    console.print("[green]✅ Do say: 'Click first claim' then 'Click analyze button'[/green]\n")
    
    try:
        with NovaAct(
            nova_act_api_key=NOVA_ACT_API_KEY,
            starting_page="http://localhost:3000",
            ignore_https_errors=True,
            max_steps=50,  # Increased step limit
            step_delay=1   # Add delay between steps
        ) as nova_act:
            
            console.print("🌐 Browser opened at http://localhost:3000")
            console.print("[green]Give me ONE simple action at a time![/green]\n")
            
            recorded_actions = []
            
            while True:
                instruction = Prompt.ask("[blue]What should I do next? (keep it simple!)[/blue]")
                
                if instruction.lower() in ['quit', 'exit', 'done']:
                    break
                
                # Check if instruction is too complex
                if len(instruction.split()) > 15:
                    console.print("[red]⚠️ That instruction is too long! Break it into smaller steps.[/red]")
                    console.print("[yellow]Example: Instead of 'Click all claims and analyze them'[/yellow]")
                    console.print("[yellow]Say: 'Click first claim' (then I'll ask for next step)[/yellow]")
                    continue
                
                console.print(f"[yellow]Executing: {instruction}[/yellow]")
                
                try:
                    result = nova_act.act(instruction)
                    console.print(f"[green]✓ Done: {result}[/green]")
                    recorded_actions.append({
                        "instruction": instruction,
                        "result": str(result),
                        "timestamp": time.time()
                    })
                except Exception as e:
                    console.print(f"[red]❌ Failed: {e}[/red]")
                    
                    # Ask if they want to try a different approach
                    retry = Prompt.ask("Try a different instruction?", choices=["yes", "no"], default="yes")
                    if retry == "no":
                        break
                
                time.sleep(1)
            
            # Save recorded session
            if recorded_actions:
                session_file = f"recorded_session_{int(time.time())}.json"
                with open(session_file, 'w') as f:
                    json.dump(recorded_actions, f, indent=2)
                
                console.print(f"[green]📁 Session saved to: {session_file}[/green]")
                
                # Generate script from recording
                script_file = generate_script_from_recording_fixed(recorded_actions)
                console.print(f"[green]🐍 Automation script: {script_file}[/green]")
    
    except Exception as e:
        console.print(f"[red]❌ Recording failed: {e}[/red]")

def generate_script_from_recording_fixed(actions):
    """Generate automation script with proper step limits"""
    
    script_filename = f"recorded_automation_{int(time.time())}.py"
    
    script_content = f'''#!/usr/bin/env python3
"""
Recorded Claims Automation - Generated from live recording
"""

import time
from nova_act import NovaAct
from rich.console import Console

console = Console()
NOVA_ACT_API_KEY = '{NOVA_ACT_API_KEY}'

def run_recorded_automation():
    """Replay recorded automation with proper limits"""
    
    console.print("[cyan]🚀 Running Recorded Automation[/cyan]")
    
    try:
        with NovaAct(
            nova_act_api_key=NOVA_ACT_API_KEY,
            starting_page="http://localhost:3000",
            ignore_https_errors=True,
            max_steps=100,  # Higher limit for replay
            step_delay=2    # Slower for reliability
        ) as nova_act:
            
            console.print("🌐 Connected to claims application")
'''
    
    for i, action in enumerate(actions, 1):
        instruction = action['instruction'].replace('"', '\\"')
        script_content += f'''
            # Recorded action {i}
            console.print("[yellow]Action {i}: {instruction}[/yellow]")
            try:
                result = nova_act.act("{instruction}")
                console.print(f"[green]✓ Result: {{result}}[/green]")
                time.sleep(2)
            except Exception as e:
                console.print(f"[red]❌ Action {i} failed: {{e}}[/red]")
'''
    
    script_content += '''
            console.print("[bold green]🎉 Recorded automation completed![/bold green]")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")

if __name__ == "__main__":
    run_recorded_automation()
'''
    
    with open(script_filename, 'w') as f:
        f.write(script_content)
    
    return script_filename

def main():
    """Main menu for fixed automation recording"""
    
    console.print("[bold cyan]🎬 Fixed Automation Recorder[/bold cyan]\n")
    console.print("[yellow]Key Rules for Live Mode:[/yellow]")
    console.print("1. Give SHORT instructions (under 15 words)")
    console.print("2. One action at a time")
    console.print("3. Let me finish before next instruction\n")
    
    live_recording_mode_fixed()

if __name__ == "__main__":
    main()
