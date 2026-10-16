from playwright.sync_api import sync_playwright
import os

TARGET = os.environ.get('AUTOTEST_TARGET', 'https://example.com')

def test_open_and_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(TARGET)
        page.wait_for_timeout(1000)
        page.screenshot(path='artifacts/playwright_example.png', full_page=True)
        browser.close()

if __name__ == '__main__':
    print('Running simple playwright script against', TARGET)
    test_open_and_screenshot()
