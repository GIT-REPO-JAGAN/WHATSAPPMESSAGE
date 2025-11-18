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

        # Try direct match
        el = page.locator(f'//span[@title="{group_name}"]')
        if el.count() > 0:
            el.first.click()
            print(f"[+] Group '{group_name}' opened.")
            return True

        # Search fallback
        search_boxes = [
            '//div[@contenteditable="true" and @data-tab and contains(@aria-label,"Search")]',
            '//div[@contenteditable="true" and @data-tab and contains(@aria-label,"Search or start new chat")]',
            '//div[@contenteditable="true" and @data-tab]',
        ]

        for sel in search_boxes:
            box = page.locator(sel)
            if box.count() > 0:
                box.first.fill(group_name)
                time.sleep(1.2)
                result = page.locator(f'//span[@title="{group_name}"]')
                if result.count() > 0:
                    result.first.click()
                    print(f"[+] Group '{group_name}' opened via search.")
                    return True

    except Exception as e:
        print(f"[ERROR opening group] {e}")

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
        print("[ERROR reading message]", e)
        return None, None


# ---------------------------------------------------
# POST MESSAGE
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
        print("[ERROR posting message]", e)
        return False


# ---------------------------------------------------
# HANDLE QR LOGIN
# ---------------------------------------------------
def ensure_logged_and_capture_qr(page):
    try:
        # If main screen not visible -> not logged in
        if page.locator('//div[@role="main"]').count() == 0:
            page.screenshot(path=QR_PATH, full_page=True)
            return False
    except Exception:
        page.screenshot(path=QR_PATH, full_page=True)
        return False

    return True


# ---------------------------------------------------
# MAIN BOT LOGIC
# ---------------------------------------------------
def run_bot():
    print("[*] Starting WhatsApp Bot...")

    with sync_playwright() as p:

        # Mobile Mode UA (QR always loads)
        mobile_user_agent = (
            "Mozilla/5.0 (Linux; Android 10; SM-G973F) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Mobile Safari/537.36"
        )

        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            args=["--no-sandbox"],
            user_agent=mobile_user_agent,
            viewport={"width": 480, "height": 900},
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # Force WhatsApp Mobile Web (QR loads reliably)
        page.goto("https://web.whatsapp.com/")
        time.sleep(3)

        # ------------------------------------------
        # LOGIN CHECK
        # ------------------------------------------
        logged = ensure_logged_and_capture_qr(page)

        if not logged:
            print("[!] Login required — QR saved as wa_qr.png")
            print("    → Open QR image (wa_qr.png)")
            print("    → Scan it using WhatsApp > Linked Devices")
            print("    → Waiting for login ...")

            for _ in range(120):
                if page.locator('//div[@role="main"]').count() > 0:
                    print("[+] Login successful!")
                    logged = True
                    break
                time.sleep(1)

        if not logged:
            print("[X] Login failed. Try scanning again.")
            browser.close()
            return

        # ------------------------------------------
        # OPEN GROUP
        # ------------------------------------------
        if not find_and_open_group(page, GROUP_NAME):
            browser.close()
            return

        print(f"[+] Watching group '{GROUP_NAME}'...")
        last_uid = None

        # ------------------------------------------
        # MESSAGE LOOP
        # ------------------------------------------
        try:
            while True:
                text, uid = get_latest_message_text(page)

                if text and uid and uid != last_uid:
                    last_uid = uid
                    print(f"[MSG] {text}")

                    reply = ask_llm(text)
                    print(f"[LLM] {reply}")

                    if POST_BACK:
                        ok = post_text_to_group(page, reply)
                        print("[POSTED]" if ok else "[POST FAILED]")

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n[!] Bot stopped manually.")

        finally:
            browser.close()
            print("[X] Browser closed. Bot stopped.")
