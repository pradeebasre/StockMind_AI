import time
from playwright.sync_api import sync_playwright

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        print("Navigating to http://localhost:8501...")
        page.goto("http://localhost:8501", timeout=30000)
        # Wait for Streamlit to load components
        time.sleep(5)
        page.screenshot(path="verification_screenshot.png", full_page=False)
        print("[SUCCESS] Screenshot captured successfully as verification_screenshot.png")
        browser.close()

if __name__ == "__main__":
    capture()
