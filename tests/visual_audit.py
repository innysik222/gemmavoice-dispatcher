"""
GemmaVoice Dispatcher — Visual & UI Audit
Tests the app at multiple viewports and captures screenshots for review.
"""
import os, time, json
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"
OUT_DIR = "/Users/krolya/PythonProjects/gemmavoice-dispatcher/tests/screenshots"

VIEWPORTS = {
    "iphone_14":  {"width": 390, "height": 844},
    "pixel_7":    {"width": 412, "height": 915},
    "ipad_mini":  {"width": 744, "height": 1133},
    "desktop_hd": {"width": 1280, "height": 720},
    "desktop_fhd": {"width": 1920, "height": 1080},
}

MOCK_PROTOCOL = (
    "**SUMMARY:** Chemical/Gas Hazard detected — Chlorine.\n"
    "**PROTOCOL:**\n"
    "1. EVACUATE UPWIND immediately.\n"
    "2. DO NOT operate electronics or light switches.\n"
    "3. Establish a 500-meter exclusion perimeter.\n"
    "4. Dispatch Hazmat unit.\n"
    "5. Consult inventory for Respirators & Hazmat Suits.\n"
    "6. Chlorine is heavier than air — move to HIGH GROUND.\n"
    "**LOGISTICS:** 30 Hazmat Suits available. 40 Respirators in stock."
)

issues = []

def audit_viewport(page, name, vp):
    """Take screenshots and check layout at a given viewport."""
    page.set_viewport_size(vp)
    page.goto(BASE_URL, wait_until="networkidle")
    time.sleep(2)

    # --- Screenshot 1: Initial state (Voice Mode) ---
    path_init = os.path.join(OUT_DIR, f"{name}_01_initial.png")
    page.screenshot(path=path_init, full_page=False)
    print(f"  [✓] {name} — initial state captured")

    # Check header visibility
    header = page.query_selector("text=GEMMAVOICE")
    if not header or not header.is_visible():
        issues.append(f"{name}: Header 'GEMMAVOICE' not visible")

    online_badge = page.query_selector("text=ONLINE")
    if not online_badge or not online_badge.is_visible():
        issues.append(f"{name}: 'ONLINE' badge not visible")

    # --- Screenshot 2: Switch to Quiet Mode ---
    voice_btn = page.query_selector("text=VOICE MODE")
    if voice_btn and voice_btn.is_visible():
        voice_btn.click()
        time.sleep(1)
        path_quiet = os.path.join(OUT_DIR, f"{name}_02_quiet_mode.png")
        page.screenshot(path=path_quiet, full_page=False)
        print(f"  [✓] {name} — quiet mode captured")

        # Check input field exists
        text_input = page.query_selector("input[placeholder='Enter manual request...']")
        if not text_input or not text_input.is_visible():
            issues.append(f"{name}: Text input field not visible in Quiet Mode")
        
        send_btn = page.query_selector("text=Send")
        if not send_btn or not send_btn.is_visible():
            issues.append(f"{name}: 'Send' button not visible in Quiet Mode")
    else:
        issues.append(f"{name}: 'VOICE MODE' button not found or not visible")

    # --- Screenshot 3: Inject mock protocol response via JS ---
    # We inject a mock response directly to test the HUD layout
    # without waiting for the LLM
    page.evaluate(f"""() => {{
        // Find the React fiber and set state directly is fragile,
        // so we dispatch a custom event that triggers the state update.
        // Instead, we'll manipulate the DOM to simulate what the HUD looks like.
        const overlayContainer = document.querySelector('.absolute.inset-4');
        if (overlayContainer) {{
            // The modal should already exist if lastResponse is set
            console.log('Overlay container found');
        }}
    }}""")

    # Since we can't easily set React state from outside,
    # let's test by sending a real query and waiting
    text_input = page.query_selector("input[placeholder='Enter manual request...']")
    if text_input and text_input.is_visible():
        text_input.fill("chlorine gas leak safety protocol")
        send_btn = page.query_selector("text=Send")
        if send_btn:
            send_btn.click()
            print(f"  [⏳] {name} — sent query, waiting for response (up to 60s)...")
            
            # Wait for the protocol text to appear
            try:
                page.wait_for_selector("text=CRITICAL PROTOCOL", timeout=60000)
                time.sleep(2)  # Let animation finish
                path_response = os.path.join(OUT_DIR, f"{name}_03_protocol_response.png")
                page.screenshot(path=path_response, full_page=False)
                print(f"  [✓] {name} — protocol response captured")

                # Check readability
                protocol_box = page.query_selector(".absolute.inset-4 div")
                if protocol_box:
                    box = protocol_box.bounding_box()
                    if box:
                        print(f"      Protocol box: {box['width']:.0f}x{box['height']:.0f} at ({box['x']:.0f},{box['y']:.0f})")
                        if box['y'] < 0:
                            issues.append(f"{name}: Protocol box is clipped at top (y={box['y']:.0f})")
                        if box['y'] + box['height'] > vp['height']:
                            issues.append(f"{name}: Protocol box overflows bottom (bottom={box['y']+box['height']:.0f} > {vp['height']})")
                        if box['width'] < 200:
                            issues.append(f"{name}: Protocol box too narrow ({box['width']:.0f}px)")
                    else:
                        issues.append(f"{name}: Could not get bounding box for protocol")
                
                # Check if text is scrollable (overflow)
                is_scrollable = page.evaluate("""() => {
                    const el = document.querySelector('.overflow-y-auto');
                    if (!el) return 'no-element';
                    return el.scrollHeight > el.clientHeight ? 'scrollable' : 'fits';
                }""")
                print(f"      Scroll state: {is_scrollable}")
                if is_scrollable == 'no-element':
                    issues.append(f"{name}: No scrollable container found for protocol text")

                # Check if Close button is visible
                close_btn = page.query_selector("text=Close")
                if not close_btn or not close_btn.is_visible():
                    issues.append(f"{name}: 'Close' button not visible on protocol modal")

                # --- Screenshot 4: After dismissing ---
                if close_btn and close_btn.is_visible():
                    close_btn.click()
                    time.sleep(1)
                    path_dismissed = os.path.join(OUT_DIR, f"{name}_04_dismissed.png")
                    page.screenshot(path=path_dismissed, full_page=False)
                    print(f"  [✓] {name} — dismissed state captured")

            except Exception as e:
                issues.append(f"{name}: Protocol response did not appear within 60s ({e})")
                path_timeout = os.path.join(OUT_DIR, f"{name}_03_timeout.png")
                page.screenshot(path=path_timeout, full_page=False)
                print(f"  [✗] {name} — timeout waiting for response")

    # --- Screenshot 5: Full page scroll ---
    path_full = os.path.join(OUT_DIR, f"{name}_05_full_page.png")
    page.screenshot(path=path_full, full_page=True)
    print(f"  [✓] {name} — full page captured")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Test on the primary demo viewport first (iPhone 14)
        name = "iphone_14"
        vp = VIEWPORTS[name]
        print(f"\n{'='*50}")
        print(f"TESTING: {name} ({vp['width']}x{vp['height']})")
        print(f"{'='*50}")
        context = browser.new_context(viewport=vp)
        page = context.new_page()
        audit_viewport(page, name, vp)
        context.close()

        # Test on desktop (the user's actual viewport)
        name = "desktop_hd"
        vp = VIEWPORTS[name]
        print(f"\n{'='*50}")
        print(f"TESTING: {name} ({vp['width']}x{vp['height']})")
        print(f"{'='*50}")
        context = browser.new_context(viewport=vp)
        page = context.new_page()
        audit_viewport(page, name, vp)
        context.close()

        browser.close()

    # --- Report ---
    print(f"\n{'='*50}")
    print("AUDIT REPORT")
    print(f"{'='*50}")
    if issues:
        print(f"\n⚠️  {len(issues)} ISSUE(S) FOUND:\n")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("\n✅ All checks passed!")
    
    print(f"\nScreenshots saved to: {OUT_DIR}/")
    print(f"Total screenshots: {len(os.listdir(OUT_DIR))}")


if __name__ == "__main__":
    main()
