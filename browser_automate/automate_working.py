#!/usr/bin/env python3
"""
FNOL Claims Processing — Natural-language sweeper (resilient, transactional scroll)
- Viewport-by-viewport: click ALL visible red 'Analyze Complexity' buttons
- For each modal: Summarize (if visible & enabled) -> wait for 'Analysis Results' -> Close (footer or top-right ×)
- Never assumes a second Summarize exists; no throw prompts
- Scroll DOWN only when the current viewport has no more red buttons
- When finished, scroll UP until 'Queue View' is visible and click it
"""

import time
import requests
from nova_act import NovaAct

BASE_URL = "http://localhost:8000"

# -------------------------- utilities --------------------------

def act_text(nova, prompt, tries=3, sleep=0.5):
    """Send a natural-language prompt and return trimmed text.
    Retries on empty output *or* transient nova.act exceptions (e.g., 5xx / invalid JSON)."""
    last = ""
    for i in range(tries):
        try:
            r = nova.act(prompt)
            last = (getattr(r, "response", "") or "").strip()
            if last:
                return last
        except Exception as e:
            print(f"ℹ️ nova.act transient error on try {i+1}/{tries}: {e}")
        time.sleep(sleep)
    return last  # may be ""


# def act_yes(nova, prompt, tries=3):
#     """YES/NO question with retry; STRICTLY forbids any interaction while answering."""
#     # Hard fence to prevent the agent from scrolling/clicking during a YES/NO probe.
#     guard = (
#         "Answer using ONE WORD ONLY (YES or NO). "
#         "Do NOT click, type, or SCROLL. Do NOT interact with the page or any popup at all. "
#         "If you are unsure, answer NO. "
#     )
#     if "Answer YES or NO" not in prompt:
#         prompt = prompt.rstrip() + " Answer YES or NO."
#     ans = (act_text(nova, guard + prompt, tries=tries) or "").strip().upper()
#     return ans.startswith("YES")

def act_yes(nova, prompt, tries=3):
    """YES/NO question with retry; enforces 'Answer YES or NO.' and forbids interactions."""
    if "Answer YES or NO" not in prompt:
        prompt = prompt.rstrip() + " Answer YES or NO."
    guard = (
        "Do not click, type, or scroll. Base your answer ONLY on what is currently visible. "
        "If you would need to interact to be sure, answer NO. "
    )
    ans = (act_text(nova, guard + prompt, tries=tries) or "").strip().upper()
    return ans.startswith("YES")


def act_click_with_ack(nova, prompt, tries=1):
    """
    Ask the agent to click something if visible/clickable and reply CLICKED/NONE.
    Returns True if it replied CLICKED.
    (tries defaults to 1 to avoid repeating actions after success.)
    """
    reply = (act_text(
        nova,
        prompt.rstrip() + " After attempting this, reply with one word: CLICKED if you clicked it, otherwise NONE.",
        tries=tries
    ) or "").strip().upper()
    return reply == "CLICKED"

# -------------------------- page/modals --------------------------

def ensure_detailed_view(nova):
    nova.act(
        "If you can see a button labeled 'Detailed View', click it once. "
        "If the page already shows a 'Queue View' button (meaning Detailed View is active), do nothing."
    )
    time.sleep(0.6)


def modal_open(nova):
    return act_yes(nova, "Without scrolling, do you currently see a popup whose title begins with 'Claim Analysis'?")


def wait_for_results(nova, attempts=5, sleep=0.8):
    """Poll for 'Analysis Results' in the open modal."""
    for _ in range(attempts):
        if act_yes(nova, "Without scrolling the page, do you see a section titled 'Analysis Results' inside the popup?"):
            return True
        time.sleep(sleep)
    return False


def close_modal(nova):
    """
    Close the claim analysis modal safely.
    - If it's already closed, return True immediately (idempotent).
    - Prefer footer 'Close', else top-right ×.
    - Never throws; success is determined by modal state, not the agent's wording.
    """
    if not modal_open(nova):
        return True

    for _ in range(2):
        # 1) Footer Close (with in-modal scroll allowance)
        if modal_open(nova):
            # _ = act_click_with_ack(
            #     nova,
            #     "Inside the open claim analysis popup, if you can see a button labeled 'Close' near the bottom of the popup, "
            #     "click it once now. If you do not see it yet, first scroll the popup content just enough to bring the 'Close' button into view, then click it.",
            #     tries=1
            # )
            _ = act_click_with_ack(
                nova,
                "Inside the open claim analysis popup (not the page behind it), if you can see a button labeled 'Close' near the bottom of the popup, "
                "click it once now. If you do not see it yet, scroll the POPUP CONTENT only—just enough to bring the 'Close' button into view—then click it. "
                "Do NOT scroll the page behind the popup.",
                tries=1
            )
            time.sleep(0.4)
            if not modal_open(nova):
                return True

        # 2) Top-right × fallback (no scrolling)
        if modal_open(nova):
            _ = act_click_with_ack(
                nova,
                "Inside the open claim analysis popup, if a top-right close icon (×) is visible, click it once now.",
                tries=1
            )
            time.sleep(0.4)
            if not modal_open(nova):
                return True

    return not modal_open(nova)


def summarize_and_close(nova):
    """
    Summarize if possible (visible & enabled), wait briefly for results, then close.
    Idempotent: if the modal is gone at any point, we stop cleanly.
    """
    if not modal_open(nova):
        return

    _ = act_click_with_ack(
        nova,
        "Inside the open claim analysis popup, if you can see a GREEN button labeled 'Summarize' "
        "and it is clickable (not greyed/disabled), click it once now.",
        tries=1
    )
    wait_for_results(nova, attempts=5, sleep=0.9)
    close_modal(nova)

# -------------------------- viewport work --------------------------

def click_one_red_button_if_visible(nova):
    """
    Click exactly ONE visible red 'Analyze Complexity' button in the current viewport (no page scroll).
    Returns True if a click happened (and handles the ensuing modal), else False.
    """
    reply = (act_text(
        nova,
        "Look only at what is currently visible on the screen. Do not scroll the PAGE yet. "
        "If you can clearly see a RED button whose text is exactly 'Analyze Complexity' and it is active (not greyed out), "
        "click that red 'Analyze Complexity' button once now. "
        "After attempting this, reply with one word: CLICKED if you clicked it, otherwise NONE.",
        tries=3  # keep robustness here
    ) or "").strip().upper()

    clicked = (reply == "CLICKED")

    # If the agent clicked but didn't reply correctly, an open modal implies success.
    if not clicked and modal_open(nova):
        clicked = True

    if clicked:
        time.sleep(0.9)
        if modal_open(nova):
            summarize_and_close(nova)
        return True

    return False


def exhaust_viewport_buttons(nova):
    """Keep clicking red buttons in this viewport until none remain. Returns count."""
    count = 0
    for _ in range(20):  # safety cap
        if modal_open(nova):
            summarize_and_close(nova)
            count += 1
            time.sleep(0.25)
            continue

        if not click_one_red_button_if_visible(nova):
            break

        count += 1
        time.sleep(0.25)  # allow DOM reflow
    return count


def at_bottom(nova):
    # Non-scrolling probe; optional in the current flow.
    return act_yes(nova, "Do not scroll. Are you already at the very bottom of this page, with no more content below the current view?")


# def scroll_down_one_viewport(nova):
#     """
#     Transactional DOWN scroll: agent must reply MOVED/NOMOVE.
#     We accept only the first move; we don't ask it to try again.
#     """
#     txt = (getattr(nova.act(
#         "Scroll DOWN exactly ONCE by about one full screen. Do not scroll more than once. Do not keep scrolling. "
#         "After you perform exactly one scroll action, reply with one word: MOVED. "
#         "If you cannot scroll because you are at the bottom already, reply with one word: NOMOVE."
#     ), "response", "") or "").strip().upper()
#     return txt == "MOVED"

# def scroll_down_one_viewport(nova):
#     """
#     Assertive, atomic DOWN move with no pre-check (pre-checks can cause the agent to scroll anyway).
#     Uses PgDn once, then a single scrollbar-track fallback. Acks MOVED/NOMOVE.
#     """
#     reply = (act_text(nova,
#         "Do this exactly once: press the Page Down (PgDn) key ONE time to move the page DOWN by about one screen. "
#         "Do NOT press Page Up. Do NOT use the mouse wheel. Do NOT perform a second scroll in this task. "
#         "Reply ONE WORD ONLY: MOVED if content moved DOWN, otherwise NOMOVE.",
#         tries=1
#     ) or "").strip().upper()

#     if reply not in ("MOVED", "NOMOVE"):
#         # One-shot fallback that still forbids a second attempt
#         reply = (act_text(nova,
#             "Single-step fallback: click the scrollbar track once BELOW the thumb to move DOWN by about one page. "
#             "Then reply ONE WORD ONLY: MOVED or NOMOVE. Do NOT try again.",
#             tries=1
#         ) or "").strip().upper()

#     return reply == "MOVED"


# def scroll_down_one_viewport(nova):
#     """
#     Atomic DOWN step that avoids key-based scrolling loops.
#     Uses a single mouse click on the scrollbar track below the thumb.
#     Returns True if the viewport moved (MOVED), else False (NOMOVE).
#     """
#     reply = (act_text(
#         nova,
#         "Using the MOUSE only: move to the vertical scrollbar and CLICK the track ONCE just BELOW the thumb. "
#         "Do not press any keys (no Page Down). Do not click a second time. "
#         "After that single click, reply with ONE WORD ONLY: MOVED if the content changed, otherwise NOMOVE.",
#         tries=1
#     ) or "").strip().upper()

#     if reply not in ("MOVED", "NOMOVE"):
#         # One-shot backup that still avoids keys & repeats
#         reply = (act_text(
#             nova,
#             "Backup: using the MOUSE WHEEL only, scroll DOWN a small amount ONCE, then STOP. "
#             "Reply with ONE WORD ONLY: MOVED or NOMOVE.",
#             tries=1
#         ) or "").strip().upper()

#     return reply == "MOVED"

def scroll_down_one_viewport(nova):
    """
    Atomic DOWN step that actually moves the claims list by ~one screen
    without letting the agent spam clicks/scrolls inside a single act.
    Returns True if something moved, else False.
    Strategy (each is a separate act; no in-act retries):
      A) Wheel-down once over the CLAIMS LIST column
      B) Page Down once (explicit 'never press twice')
      C) Small nudge: press Arrow Down three times quickly
    """

    # A) Mouse wheel once over the list (no clicking the scrollbar)
    reply = (act_text(
        nova,
        "Perform EXACTLY ONE action, then IMMEDIATELY answer.\n"
        "Move the mouse over the CLAIMS LIST (the center column showing cards with 'Type', 'Date of Loss', etc.). "
        "With the mouse wheel, scroll DOWN a small amount ONE TIME ONLY. "
        "Do NOT click the scrollbar. Do NOT press any keys. Do NOT try a second scroll.\n"
        "Now reply with ONE WORD ONLY: MOVED if content shifted, otherwise NOMOVE.",
        tries=1
    ) or "").strip().upper()
    if reply == "MOVED":
        time.sleep(0.2)  # let DOM settle
        return True
    if reply == "NOMOVE":
        pass
    else:
        # If they didn't follow the format, keep going but do not re-issue A.
        pass

    # B) Page Down once (key-based, but explicitly forbid repeat)
    reply = (act_text(
        nova,
        "Perform EXACTLY ONE keyboard action, then IMMEDIATELY answer.\n"
        "Press Page Down ONE time and STOP. Do NOT press it a second time under ANY circumstance. "
        "Do NOT click. Do NOT use the mouse wheel.\n"
        "Reply with ONE WORD ONLY: MOVED if content shifted, otherwise NOMOVE.",
        tries=1
    ) or "").strip().upper()
    if reply == "MOVED":
        time.sleep(0.2)
        return True
    if reply == "NOMOVE":
        pass
    else:
        pass

    # C) Small nudge (helps when focus is off the scrollable div)
    reply = (act_text(
        nova,
        "Final nudge: tap the Arrow Down key THREE times quickly (tap-tap-tap), then STOP. "
        "Do NOT press any other keys. Do NOT scroll again.\n"
        "Reply with ONE WORD ONLY: MOVED if content shifted, otherwise NOMOVE.",
        tries=1
    ) or "").strip().upper()
    return reply == "MOVED"




def scroll_up_one_viewport(nova):
    """Assertive, atomic UP move with a clear one-word ack."""
    reply = (act_text(nova,
        "Do this exactly once: press the Page Up (PgUp) key ONE time to move the page UP by about one screen. "
        "Do NOT press Page Down. Do NOT use the mouse wheel. Do NOT scroll the page behind any popup. "
        "Reply with ONE WORD ONLY: MOVED if content moved UP, otherwise NOMOVE.",
        tries=2
    ) or "").strip().upper()

    if reply not in ("MOVED", "NOMOVE"):
        reply = (act_text(nova,
            "Single action fallback: click the scrollbar track once just ABOVE the thumb to move UP by about one page. "
            "Then reply ONE WORD ONLY: MOVED or NOMOVE.",
            tries=1
        ) or "").strip().upper()

    return reply == "MOVED"

# -------------------------- navigation back to Queue View --------------------------

# def go_back_to_queue_view(nova):
#     """
#     Get back to 'Queue View' from the bottom, simply and assertively:
#       1) Try to click it if already visible.
#       2) Press Home once, then try to click.
#       3) Walk up with Page Up (ack MOVED/NOMOVE) and try after each step.
#       4) Final fallback: 'Scroll to the very top', then try to click.
#     """
#     def click_queue():
#         return (
#             act_click_with_ack(nova, "If a button labeled 'Queue View' is visible right now, click it once now.", tries=1)
#             or act_click_with_ack(nova, "If you see a text link or tab labeled 'Queue View', click it once now.", tries=1)
#         )

#     # 1) No-scroll attempt
#     if click_queue():
#         print("✅ Queue View clicked.")
#         return True

#     # 2) Home to jump near top
#     _ = act_text(nova,
#         "Do this exactly once: press the Home key ONE time to jump to the TOP of the page. "
#         "Do NOT press End. Reply with ONE WORD ONLY: DONE.",
#         tries=2
#     )
#     time.sleep(0.2)
#     if click_queue():
#         print("✅ Queue View clicked.")
#         return True

#     # 3) Page Up steps with tries after each move
#     for _ in range(16):
#         moved = scroll_up_one_viewport(nova)
#         if click_queue():
#             print("✅ Queue View clicked.")
#             return True
#         if not moved:  # already at the top
#             break

#     # 4) Final fallback
#     _ = act_text(nova, "Scroll to the very top of the page. When finished, reply with one word: DONE.", tries=2)
#     if click_queue():
#         print("✅ Queue View clicked.")
#         return True

#     print("ℹ️ Reached top; Queue View not found.")
#     return False

def go_back_to_queue_view(nova):
    """
    Get back to 'Queue View' without relying on the Home key (agent keeps clicking instead).
    Strategy:
      1) Try to click it if already visible (no scroll).
      2) One-shot jump: 'Scroll to the very top of the page' (single act).
      3) Walk up with Page Up (our scroll_up_one_viewport) and try after each step.
      4) Final fallback: 'Scroll to the very top' again, then try the click.
    """
    def click_queue():
        return (
            act_click_with_ack(nova, "Do not scroll. If a button labeled 'Queue View' is visible right now, click it once now.", tries=1)
            or act_click_with_ack(nova, "Do not scroll. If you see a text link or tab labeled 'Queue View', click it once now.", tries=1)
        )

    # 1) No-scroll attempt
    if click_queue():
        print("✅ Queue View clicked.")
        return True

    # 2) One-shot jump-to-top (avoid 'Home' which the agent mishandles)
    _ = act_text(
        nova,
        "Scroll the PAGE to the very top in a SINGLE action and then STOP. "
        "Do not press End. Do not scroll back down. Reply with ONE WORD ONLY: DONE.",
        tries=1
    )
    time.sleep(0.25)
    if click_queue():
        print("✅ Queue View clicked.")
        return True

    # 3) Page Up steps; attempt click after each
    for _ in range(16):
        moved = scroll_up_one_viewport(nova)  # already returns True/False (MOVED/NOMOVE)
        if click_queue():
            print("✅ Queue View clicked.")
            return True
        if not moved:
            break  # likely at top

    # 4) Final fallback
    _ = act_text(nova, "Scroll to the very top of the page. When finished, reply with one word: DONE.", tries=1)
    if click_queue():
        print("✅ Queue View clicked.")
        return True

    print("ℹ️ Reached top; Queue View not found.")
    return False


# -------------------------- main --------------------------

def main():
    print("🤖 FNOL Claims — natural-language sweeper (resilient, transactional scroll)")

    # Connectivity check
    print("🔍 Checking app...")
    try:
        response = requests.get(BASE_URL, timeout=10)
        if response.status_code != 200:
            print(f"❌ App not reachable. Status: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ App not reachable: {e}")
        return
    print("✅ App reachable")

    try:
        with NovaAct(
            starting_page=BASE_URL,
            ignore_https_errors=True,
            headless=False,
            record_video=False
        ) as nova:
            print("🌐 Opening FNOL…")
            time.sleep(1.0)

            print("📋 Switching to Detailed View (if needed)…")
            ensure_detailed_view(nova)

            print("⤴️ Jumping to the top of the list…")
            nova.act("Scroll to the very top of the page.")
            time.sleep(0.5)

            total_processed = 0

            for attempt in range(1, 200):
                print(f"\n🔄 Attempt {attempt}: finish all visible red buttons in this viewport…")

                # Clear any open modal first
                if modal_open(nova):
                    summarize_and_close(nova)
                    total_processed += 1
                    print("ℹ️ Cleared a modal already open.")
                    continue

                processed_here = exhaust_viewport_buttons(nova)
                total_processed += processed_here

                if processed_here > 0:
                    print(f"✅ Cleared {processed_here} red button(s) in this viewport; re-checking here before moving on.")
                    continue

                # No buttons here — try one transactional DOWN scroll.
                moved = scroll_down_one_viewport(nova)
                if not moved:
                    print("🏁 Bottom reached (NOMOVE). No more red buttons below.")
                    break

            print(f"\n📊 Total claims processed: {total_processed}")

            # Head back to Queue View (scroll up as needed)
            print("↩️ Returning to Queue View…")
            go_back_to_queue_view(nova)

            print("\n🎉 Done!")

    except Exception as e:
        print(f"❌ Automation failed: {e}")

if __name__ == "__main__":
    main()
