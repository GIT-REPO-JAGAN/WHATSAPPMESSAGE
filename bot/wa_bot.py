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


# ---------------------------------------------------
# FIND AND OPEN GROUP
# ---------------------------------------------------
def find_and_open_group(page, group_name):
    try:
        page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)

        # Direct match
        el = page.locator(f'//span[@title="{group_name}"]')
        if el.count() > 0:
            el.first.click()
            print(f"[+] Group '{group_name}' opened.")
            return True

        # Search fallback
        search_selectors = [
            '//div[@contenteditable="true" and @data-tab and contains(@aria-label,"Search")]',
            '//div[@contenteditable="true" and @data-tab and contains(@aria-label,"Search or start new chat")]',
            '//div[@contenteditable="true" and @data-tab]',
        ]

        for sel in search_selectors:
            box = page.locator(sel)
            if box.count() > 0:
                box.first.fill(group_name)
                time.sleep(1.5)
                result = page.locator(f'//span[@title="{group_name}"]')
                if result.count() > 0:
                    result.first.click()
                    print(f"[+] Group '{group_name}' opened via search.")
                    return True

    except Exception as e:
        print(f"[ERROR] Opening group: {e}")

    print(f"[!] Group '{group_name}' not found.")
    return False


# ---------------------------------------------------
# GET LATEST MESSAGE
# ---------------------------------------------------
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


# ---------------------------------------------------
# POST LLM RESPONSE
# ---------------------------------------------------
def post_text_to_group(page, text):
    try:
        inp = page.locator('//div[@contenteditable="true" and @data-tab]')
        if inp.count() == 0:
            print("[!] Message input box not found.")
            return False

        inp.first.click()
        inp.first.fill(text)
        page.keyboard.press("Enter")
        return True

    except Exception as e:
        print("[ERROR] Posting message:", e)
        return False


# ---------------------------------------------------
# QR HANDLING
# ---------------------------------------------------
def ensure_logged_and_capture_qr(page):
    try:
        if page.locator('//div[@role="main"]').count() == 0:
            page.screenshot(path=QR_PATH, full_page=True)
            return False
    except Exception:
        page.screenshot(path=QR_PATH, full_page=True)
        return False

    return True


# ---------------------------------------------------
# MAIN BOT RUNNER
# ---------------------------------------------------
def run_bot():
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:
        # --------------------------------------------
        # FIX: MODERN CHROME USER-AGENT FOR WHATSAPP
        # --------------------------------------------
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            args=["--no-sandbox"],
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")

        time.sleep(2)

        # --------------------------------------------
        # Check login / show QR
        # --------------------------------------------
        logged = ensure_logged_and_capture_qr(page)
        if not logged:
            print("[!] Login required — QR saved as wa_qr.png")
            print("    → Open wa_qr.png")
            print("    → Scan using WhatsApp → Linked Devices")
            print("    → Waiting for login...")

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

        # --------------------------------------------
        # OPEN GROUP
        # --------------------------------------------
        if not find_and_open_group(page, GROUP_NAME):
            browser.close()
            return

        print(f"[+] Watching group '{GROUP_NAME}' for new messages...")
        last_uid = None

        # --------------------------------------------
        # MAIN LOOP
        # --------------------------------------------
        try:
            while True:
                text, uid = get_latest_message_text(page)

                if text and uid and uid != last_uid:
                    last_uid = uid
                    print(f"[MSG] {text}")

                    reply = ask_llm(text)
                    print(f"[LLM] {reply}")

                    if POST_BACK:
                        posted = post_text_to_group(page, reply)
                        print("[POSTED]" if posted else "[FAILED TO POST]")

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n[!] Bot stopped manually.")

        finally:
            browser.close()
            print("[X] Browser closed. Bot stopped.")
