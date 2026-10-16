from playwright.sync_api import sync_playwright
import os
import time
from pathlib import Path

# Gooddaygoobuy221/tests_playwright/register_autodesk.py
# Automated registration script for Autodesk registration page.
# USAGE (locally):
#   AUTOTEST_TARGET=https://accounts.autodesk.com/register \
#   AUTOTEST_USER=testuser@example.com \
#   AUTOTEST_PASS=SuperSecret123 \
#   python3 Gooddaygoobuy221/tests_playwright/register_autodesk.py

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

TARGET = os.environ.get("AUTOTEST_TARGET") or "https://accounts.autodesk.com/register"
USER = os.environ.get("AUTOTEST_USER")
PASSW = os.environ.get("AUTOTEST_PASS")

if not USER or not PASSW:
    print("AUTOTEST_USER and AUTOTEST_PASS must be set as environment variables. Exiting.")
    raise SystemExit(2)


def _screenshot(page, name):
    path = ARTIFACTS / name
    page.screenshot(path=str(path), full_page=True)
    print("Saved screenshot:", path)


def run_registration(headless=True, timeout=60000):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        print(f"Navigating to {TARGET}")
        page.goto(TARGET, timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)

        # The real Autodesk registration page may have different selectors.
        # Try several common possibilities; if none found, save screenshot and exit.
        try_selectors = [
            ('input[name="email"]', 'input#email'),
            ('input[name="userName"]', 'input[type="email"]')
        ]

        email_filled = False
        for sel_group in try_selectors:
            for sel in sel_group:
                try:
                    if page.query_selector(sel):
                        page.fill(sel, USER)
                        email_filled = True
                        print("Filled email using selector:", sel)
                        break
                except Exception:
                    continue
            if email_filled:
                break

        # Try to fill password fields
        pwd_filled = False
        pwd_selectors = ['input[name="password"]', 'input[type="password"]', 'input#password']
        for sel in pwd_selectors:
            try:
                if page.query_selector(sel):
                    page.fill(sel, PASSW)
                    # try confirm field if exists
                    conf = page.query_selector('input[name="confirmPassword"]') or page.query_selector('input#confirmPassword')
                    if conf:
                        conf.fill(PASSW)
                    pwd_filled = True
                    print("Filled password using selector:", sel)
                    break
            except Exception:
                continue

        if not email_filled or not pwd_filled:
            print("Could not find expected registration fields. Saving page screenshot and exiting.")
            _screenshot(page, "register_fields_missing.png")
            browser.close()
            return False

        # check for captcha iframes
        captchas = page.query_selector_all('iframe[src*="recaptcha"]') + page.query_selector_all('div.g-recaptcha')
        if captchas:
            print("CAPTCHA detected. Will switch to interactive headful mode for manual solve.")
            _screenshot(page, "register_before_captcha.png")
            browser.close()
            if headless:
                return run_registration(headless=False)
            else:
                print("Please solve the CAPTCHA in the opened browser. After solving, come back to the terminal and press Enter to continue.")
                input("Press Enter after solving CAPTCHA...")
                # Re-open page in same context (assumes cookies/session preserved)
                # Note: For simplicity we re-open the target page
                with sync_playwright() as p2:
                    browser2 = p2.chromium.launch(headless=False)
                    page2 = browser2.new_page()
                    page2.goto(TARGET, timeout=timeout)
                    page2.wait_for_load_state("networkidle", timeout=timeout)
                    _screenshot(page2, "register_after_manual_captcha.png")
                    # Attempt to click submit
                    try:
                        if page2.query_selector('button[type="submit"]'):
                            page2.click('button[type="submit"]')
                    except Exception as e:
                        print("Could not submit after manual CAPTCHA:", e)
                    browser2.close()
                return True

        # submit the form (try common submit selectors)
        submit_selectors = ['button[type="submit"]', 'input[type="submit"]', 'button[name="register"]']
        submitted = False
        for sel in submit_selectors:
            try:
                if page.query_selector(sel):
                    page.click(sel)
                    submitted = True
                    print("Clicked submit using selector:", sel)
                    break
            except Exception:
                continue

        if not submitted:
            print("Could not find submit button; saving screenshot and exiting.")
            _screenshot(page, "register_no_submit.png")
            browser.close()
            return False

        # wait for navigation or confirmation
        try:
            page.wait_for_load_state('networkidle', timeout=30000)
        except Exception:
            pass

        time.sleep(2)
        _screenshot(page, "register_after_submit.png")

        # Heuristic: check URL change or presence of verification text
        url = page.url
        success = False
        try:
            if any(x in url.lower() for x in ['verify', 'welcome', 'confirm', 'dashboard']):
                success = True
            else:
                # look for verification prompts
                if page.query_selector('text=Verify') or page.query_selector('text=Check your email') or page.query_selector('text=Welcome'):
                    success = True
        except Exception:
            success = False

        print("Registration heuristic result:", success, "(current url:", url, ")")
        browser.close()
        return success


if __name__ == '__main__':
    ok = run_registration(headless=True)
    print('Registration completed:', ok)
