# wa_bot.py
import os
import time
from playwright.sync_api import sync_playwright

from bot.config import (
    GROUP_NAME,
    POLL_INTERVAL,
    USER_DATA_DIR,
    QR_PATH,
    POST_BACK,
)
from bot.llm import ask_llm


def find_and_open_group(page, group_name):
    try:
        page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)

        # Try direct match first
        el = page.locator(f'//span[@title="{group_name}"]')
        if el.count() > 0:
            el.first.click()
            print(f"[+] Group '{group_name}' opened.")
            return True

        # Fallback to search
        search_boxes = [
            '//div[@contenteditable="true" and @data-tab and contains(@aria-label,"Search")]',
            '//div[@contenteditable="true" and @data-tab and contains(@aria-label,"Search or start new chat")]',
            '//div[@contenteditable="true" and @data-tab]'
        ]

        for sel in search_boxes:
            box = page.locator(sel)
            if box.count() > 0:
                box.first.fill(group_name)
                time.sleep(1.2)
                result = page.locator(f'//span[@title="{group_name}"]')
                if result.count() > 0:
                    result.first.click()
                    print(f"[+] Group '{group_name}' opened by search.")
                    return True
    except Exception as e:
        print("[ERROR] Group search error:", e)

    print(f"[!] Group '{group_name}' not found.")
    return False


def get_latest_message_text(page):
    try:
        locator = page.locator(
            '//div[contains(@class,"message-in") or contains(@class,"message-out")]'
            '//span[@dir="ltr" or @dir="auto"]'
        )

        count = locator.count()
        if count == 0:
            return None, None

        last = locator.nth(count - 1)
        text = last.inner_text().strip()
        uid = f"{hash(text)}_{count}"

        return text, uid

    except Exception as e:
        print("[ERROR] Reading message:", e)
        return None, None


def post_text_to_group(page, text):
    try:
        inp = page.locator('//div[@contenteditable="true" and @data-tab]')
        if inp.count() == 0:
            print("[!] Message box not found.")
            return False

        inp.first.click()
        inp.first.fill(text)
        page.keyboard.press("Enter")
        return True

    except Exception as e:
        print("[ERROR] Posting message:", e)
        return False


def ensure_logged_and_capture_qr(page):
    # Check if we are logged in (main UI visible)
    try:
        if page.locator('//div[@role="main"]').count() == 0:
            # Not logged in – save the QR
            page.screenshot(path=QR_PATH, full_page=True)
            return False
    except Exception:
        page.screenshot(path=QR_PATH, full_page=True)
        return False

    return True


def run_bot():
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            args=["--no-sandbox"]
        )

        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")

        time.sleep(2)

        logged = ensure_logged_and_capture_qr(page)
        if not logged:
            print("[!] Not logged in. QR saved as", QR_PATH)
            print("    → Open wa_qr.png and scan it using WhatsApp → Linked Devices")
            print("    → Waiting for login...")

            # Wait until the UI loads
            for _ in range(120):
                if page.locator('//div[@role="main"]').count() > 0:
                    logged = True
                    print("[+] Login successful!")
                    break
                time.sleep(1)

        if not logged:
            print("[X] Login not completed. Stopping bot.")
            browser.close()
            return

        # Open the proper group
        if not find_and_open_group(page, GROUP_NAME):
            browser.close()
            return

        print(f"[+] Watching group '{GROUP_NAME}' for new messages...")
        last_uid = None

        try:
            while True:
                text, uid = get_latest_message_text(page)

                if text and uid and uid != last_uid:
                    last_uid = uid
                    print(f"[MSG] {text}")

                    # Send to LLM
                    reply = ask_llm(text)
                    print(f"[LLM] {reply}")

                    # Auto-reply back to WhatsApp group
                    if POST_BACK:
                        success = post_text_to_group(page, reply)
                        print("[POSTED]" if success else "[FAILED POST]")

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n[!] Bot stopped manually.")

        finally:
            browser.close()
            print("[X] Browser closed. Bot stopped.")
