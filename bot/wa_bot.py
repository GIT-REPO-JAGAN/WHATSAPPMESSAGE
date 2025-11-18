# wa_bot.py
import os
import time
from playwright.sync_api import sync_playwright
from .config import GROUP_NAME, POLL_INTERVAL, USER_DATA_DIR, QR_PATH, POST_BACK
from .llm import ask_llm

def find_and_open_group(page, group_name):
    # wait for chat list
    page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)
    # try title selector first
    try:
        el = page.locator(f'//span[@title="{group_name}"]')
        if el.count() > 0:
            el.first.click()
            return True
    except Exception:
        pass
    # fall back to search
    try:
        # Try different search selectors
        search_selectors = [
            '//div[@contenteditable="true" and @data-tab and contains(@aria-label,"Search")]',
            '//div[@contenteditable="true" and @data-tab and contains(@aria-label,"Search or start new chat")]',
            '//div[@contenteditable="true" and @data-tab]'
        ]
        for sel in search_selectors:
            box = page.locator(sel)
            if box.count() > 0:
                box.first.fill(group_name)
                time.sleep(1)
                result = page.locator(f'//span[@title="{group_name}"]')
                if result.count() > 0:
                    result.first.click()
                    return True
    except Exception:
        pass
    return False

def get_latest_message_text(page):
    try:
        # locate message text spans and take last
        locator = page.locator('//div[contains(@class,"message-in") or contains(@class,"message-out")]//span[@dir="ltr" or @dir="auto"]')
        count = locator.count()
        if count == 0:
            return None, None
        last_idx = count - 1
        text = locator.nth(last_idx).inner_text().strip()
        uid = f"{hash(text)}_{last_idx}"
        return text, uid
    except Exception as e:
        return None, None

def post_text_to_group(page, text):
    try:
        inp = page.locator('//div[@contenteditable="true" and @data-tab]')
        if inp.count() == 0:
            return False
        inp.first.click()
        inp.first.fill(text)
        page.keyboard.press("Enter")
        return True
    except Exception:
        return False

def ensure_logged_and_capture_qr(page):
    # If the page shows QR prompt, save screenshot so user can scan in Codespaces
    try:
        # QR usually appears inside canvas or img; detect login state by presence of main UI
        if page.locator('//div[@role="main"]').count() == 0:
            # not fully logged-in: capture QR screenshot
            page.screenshot(path=QR_PATH, full_page=True)
            return False
    except Exception:
        page.screenshot(path=QR_PATH, full_page=True)
        return False
    return True

def run_bot():
    with sync_playwright() as p:
        browser_context = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=True, args=["--no-sandbox"])
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        page.goto("https://web.whatsapp.com")
        # wait up to 2 min for UI or QR
        time.sleep(2)
        logged = ensure_logged_and_capture_qr(page)
        if not logged:
            print(f"Not logged in. QR screenshot saved as {QR_PATH}. Scan it from your phone in WhatsApp -> Link device.")
            # Wait until user scans and the main UI loads
            print("Waiting for login... (check QR image or refresh file view)")
            # poll for login
            for _ in range(120):
                try:
                    if page.locator('//div[@role="main"]').count() > 0:
                        logged = True
                        break
                except Exception:
                    pass
                time.sleep(1)
        if not logged:
            print("Login not completed. Exiting.")
            browser_context.close()
            return

        if not find_and_open_group(page, GROUP_NAME):
            print(f"Group '{GROUP_NAME}' not found in visible chat list.")
            browser_context.close()
            return

        last_uid = None
        print(f"Watching group '{GROUP_NAME}' for new messages...")
        try:
            while True:
                text, uid = get_latest_message_text(page)
                if text and uid and uid != last_uid:
                    last_uid = uid
                    print("New message:", text)
                    reply = ask_llm(text)
                    print("LLM reply:", reply)
                    if POST_BACK:
                        posted = post_text_to_group(page, reply)
                        print("Posted back:", posted)
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("Stopping bot.")
        finally:
            browser_context.close()
