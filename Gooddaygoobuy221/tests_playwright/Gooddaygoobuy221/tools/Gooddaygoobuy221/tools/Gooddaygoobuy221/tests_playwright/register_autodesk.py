from playwright.sync_api import sync_playwright
import os
from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

TARGET = os.environ.get("AUTOTEST_TARGET") or "https://accounts.autodesk.com/register"
USER = os.environ.get("AUTOTEST_USER")
PASSW = os.environ.get("AUTOTEST_PASS")

if not USER or not PASSW:
    raise SystemExit("Set AUTOTEST_USER and AUTOTEST_PASS before running this script.")

def save(page, name):
    page.screenshot(path=str(ARTIFACTS / name), full_page=True)
    print(f"Saved screenshot: {ARTIFACTS / name}")

def run_registration(headless=True):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(TARGET, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

        selectors = ['input[name="email"]', 'input[name="userName"]', 'input[type="email"]', 'input[id="email"]']
        email_filled = False
        for s in selectors:
            try:
                if page.query_selector(s):
                    page.fill(s, USER)
                    email_filled = True
                    print("Email filled using:", s)
                    break
            except Exception:
                pass

        pwd_selectors = ['input[name="password"]', 'input[type="password"]', 'input[id="password"]']
        password_filled = False
        for s in pwd_selectors:
            try:
                if page.query_selector(s):
                    page.fill(s, PASSW)
                    conf = page.query_selector('input[name="confirmPassword"]') or page.query_selector('input[id="confirmPassword"]')
                    if conf:
                        conf.fill(PASSW)
                    password_filled = True
                    print("Password filled using:", s)
                    break
            except Exception:
                pass

        if not email_filled or not password_filled:
            save(page, "register_missing_fields.png")
            browser.close()
            return False

        if page.query_selector('iframe[src*="recaptcha"]') or page.query_selector('div.g-recaptcha'):
            print("CAPTCHA detected. Opening in headful mode.")
            save(page, "register_before_captcha.png")
            browser.close()
            if headless:
                return run_registration(headless=False)
            else:
                print("Solve CAPTCHA manually, then press Enter.")
                input("After solving CAPTCHA, press Enter: ")
                with sync_playwright() as p2:
                    browser2 = p2.chromium.launch(headless=False)
                    page2 = browser2.new_page()
                    page2.goto(TARGET, timeout=60000)
                    page2.wait_for_load_state("networkidle", timeout=30000)
                    save(page2, "register_after_manual_captcha.png")
                    browser2.close()
                return True

        click_selectors = ['button[type="submit"]', 'input[type="submit"]', 'button[name="register"]']
        clicked = False
        for s in click_selectors:
            try:
                if page.query_selector(s):
                    page.click(s)
                    clicked = True
                    print("Clicked submit using:", s)
                    break
            except Exception:
                pass

        if not clicked:
            save(page, "register_submit_missing.png")
            browser.close()
            return False

        page.wait_for_timeout(2000)
        save(page, "register_after_submit.png")
        browser.close()
        return True

if __name__ == "__main__":
    ok = run_registration(headless=True)
    print("Registration attempt result:", ok)
