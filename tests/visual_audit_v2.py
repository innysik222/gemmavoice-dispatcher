"""
GemmaVoice Dispatcher — Visual Audit v2
Focused test: sends a query, waits for the REAL LLM response, then screenshots.
Tests both iPhone and Desktop viewports.
"""
import os, time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"
OUT_DIR = "/Users/krolya/PythonProjects/gemmavoice-dispatcher/tests/screenshots_v2"

VIEWPORTS = {
    "iphone_14":  {"width": 390, "height": 844},
    "desktop_hd": {"width": 1280, "height": 720},
}

issues = []

def test_viewport(browser, name, vp):
    print(f"\n{'='*50}")
    print(f"TESTING: {name} ({vp['width']}x{vp['height']})")
    print(f"{'='*50}")
    
    context = browser.new_context(viewport=vp)
    page = context.new_page()
    page.goto(BASE_URL, wait_until="networkidle")
    time.sleep(2)

    # 1. Initial state — should NOT show CRITICAL PROTOCOL modal
    path = os.path.join(OUT_DIR, f"{name}_01_clean_boot.png")
    page.screenshot(path=path, full_page=False)
    print(f"  [✓] Clean boot captured")
    
    protocol_modal = page.query_selector("text=CRITICAL PROTOCOL")
    if protocol_modal and protocol_modal.is_visible():
        issues.append(f"{name}: CRITICAL PROTOCOL modal visible on boot (should be hidden)")
    else:
        print(f"  [✓] No protocol modal on boot — GOOD")

    # 2. Switch to Quiet Mode
    voice_btn = page.query_selector("text=VOICE MODE")
    if voice_btn:
        voice_btn.click()
        time.sleep(1)

    # 3. Send a chlorine query
    text_input = page.query_selector("input[placeholder='Enter manual request...']")
    if text_input:
        text_input.fill("chlorine gas leak protocol")
        send_btn = page.query_selector("text=Send")
        if send_btn:
            send_btn.click()
            print(f"  [⏳] Query sent. Waiting up to 120s for REAL response...")
            
            # Wait for "PROCESSING FIELD NOTES..." to appear first
            try:
                page.wait_for_selector("text=PROCESSING FIELD NOTES", timeout=10000)
                print(f"  [✓] Processing state detected")
                
                path = os.path.join(OUT_DIR, f"{name}_02_processing.png")
                page.screenshot(path=path, full_page=False)
            except:
                print(f"  [!] Processing state not detected, continuing...")
            
            # Now wait for the REAL response (text changes from "PROCESSING...")
            # We poll until the text changes
            start = time.time()
            max_wait = 120
            got_response = False
            while time.time() - start < max_wait:
                content = page.evaluate("""() => {
                    const els = document.querySelectorAll('.whitespace-pre-wrap');
                    for (const el of els) {
                        if (el.textContent && !el.textContent.includes('PROCESSING') && el.textContent.length > 30) {
                            return el.textContent.substring(0, 200);
                        }
                    }
                    return null;
                }""")
                if content:
                    print(f"  [✓] Real response detected ({len(content)} chars): {content[:80]}...")
                    got_response = True
                    break
                time.sleep(3)
            
            if got_response:
                time.sleep(2)  # Let rendering settle
                
                # Screenshot the response
                path = os.path.join(OUT_DIR, f"{name}_03_response.png")
                page.screenshot(path=path, full_page=False)
                print(f"  [✓] Response screenshot captured")
                
                # Check if the modal is properly contained
                modal = page.query_selector(".absolute.inset-4 > div")
                if modal:
                    box = modal.bounding_box()
                    if box:
                        print(f"      Modal box: {box['width']:.0f}w x {box['height']:.0f}h at ({box['x']:.0f}, {box['y']:.0f})")
                        
                        # Check clipping
                        if box['y'] < 0:
                            issues.append(f"{name}: Modal clipped at TOP (y={box['y']:.0f}px)")
                        if box['y'] + box['height'] > vp['height']:
                            issues.append(f"{name}: Modal overflows BOTTOM ({box['y']+box['height']:.0f} > {vp['height']})")
                        if box['x'] < 0:
                            issues.append(f"{name}: Modal clipped at LEFT")
                        if box['x'] + box['width'] > vp['width']:
                            issues.append(f"{name}: Modal overflows RIGHT")
                        
                        # Check the modal fits within the camera section
                        camera = page.query_selector("section.relative")
                        if camera:
                            cam_box = camera.bounding_box()
                            if cam_box:
                                if box['y'] < cam_box['y']:
                                    issues.append(f"{name}: Modal extends above camera section")
                                if box['y'] + box['height'] > cam_box['y'] + cam_box['height']:
                                    issues.append(f"{name}: Modal extends below camera section")
                    else:
                        issues.append(f"{name}: Could not get modal bounding box")
                
                # Check scroll state
                scroll_info = page.evaluate("""() => {
                    const el = document.querySelector('.overflow-y-auto');
                    if (!el) return {found: false};
                    return {
                        found: true,
                        scrollHeight: el.scrollHeight,
                        clientHeight: el.clientHeight,
                        scrollable: el.scrollHeight > el.clientHeight
                    };
                }""")
                print(f"      Scroll info: {scroll_info}")
                if scroll_info.get('scrollable'):
                    print(f"  [✓] Text is scrollable (content={scroll_info['scrollHeight']}px, visible={scroll_info['clientHeight']}px)")
                elif scroll_info.get('found'):
                    print(f"  [✓] Text fits without scrolling")
                else:
                    issues.append(f"{name}: No scrollable container found")

                # Check Close button
                close_btn = page.query_selector("text=Close")
                if close_btn and close_btn.is_visible():
                    print(f"  [✓] Close button visible")
                    close_btn.click()
                    time.sleep(1)
                    path = os.path.join(OUT_DIR, f"{name}_04_dismissed.png")
                    page.screenshot(path=path, full_page=False)
                    print(f"  [✓] Dismissed state captured")
                else:
                    issues.append(f"{name}: Close button not visible")
            else:
                issues.append(f"{name}: LLM response did not arrive within {max_wait}s")
                path = os.path.join(OUT_DIR, f"{name}_03_timeout.png")
                page.screenshot(path=path, full_page=False)

    context.close()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for name, vp in VIEWPORTS.items():
            test_viewport(browser, name, vp)
        
        browser.close()

    # Report
    print(f"\n{'='*50}")
    print("VISUAL AUDIT REPORT")
    print(f"{'='*50}")
    if issues:
        print(f"\n⚠️  {len(issues)} ISSUE(S) FOUND:\n")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("\n✅ ALL CHECKS PASSED!")
    
    print(f"\nScreenshots: {OUT_DIR}/")


if __name__ == "__main__":
    main()
