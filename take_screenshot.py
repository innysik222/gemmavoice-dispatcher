from playwright.sync_api import sync_playwright
import time

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    # Set viewport to mobile size
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    page = context.new_page()
    page.goto('http://localhost:3000')
    time.sleep(2)
    page.screenshot(path='/Users/krolya/PythonProjects/gemmavoice-dispatcher/ui_test_full.png')
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
