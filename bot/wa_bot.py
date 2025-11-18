import time
import os
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME, DEBUG


USER_DATA_DIR = os.path.join(os.getcwd(), "wa_user_data")


def log(msg):
    if DEBUG:
        print(msg)


def run_bot():
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:

        # --- LAUNCH REAL CHROME HEADLESS ---
        print("[*] Launching real Google Chrome (headless)...")

        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,     # headless MUST be true for systemd
            executable_path="/usr/bin/google-chrome",
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                "--disable-web-security",
                "--disable-site-isolation-trials",
                "--window-size=1366,768"
            ]
        )

        page = browser.new_page()

        # --- OPEN WHATSAPP ---
        print("[*] Opening WhatsApp Web...")
        page.goto("https://web.whatsapp.com", wait_until="networkidle")

        # --- LOGIN CHECK ---
        print("[*] Checking login status...")

        try:
            page.wait_for_selector("canvas[aria-label='Scan me!']", timeout=5000)
            # QR exists → not logged in
            page.screenshot(path="wa_qr.png")
            print("[!] Login required. QR saved → wa_qr.png")
            print("    Scan it from your phone: WhatsApp → Linked Devices")
            return
        except:
            print("[+] Logged in successfully!")

        # --- FIND GROUP ---
        print(f"[*] Searching for group: {GROUP_NAME}")

        SEARCH_SELECTORS = [
            "div[role='textbox']",
            "div[aria-label='Search input textbox']",
            "div[contenteditable='true']",
        ]

        search_box = None

        for selector in SEARCH_SELECTORS:
            try:
                sb = page.locator(selector).first
                if sb.is_visible():
                    search_box = sb
                    break
            except:
                pass

        if not search_box:
            print("[ERROR] Search box not found!")
            browser.close()
            return

        # Click search box
        search_box.click()
        time.sleep(1)
        search_box.fill(GROUP_NAME)
        time.sleep(2)

        # Click the group
        try:
            grp = page.locator(f"text={GROUP_NAME}").first
            grp.click()
            print("[*] Group opened successfully!")
        except Exception as e:
            print("[ERROR] Could not open group:", e)
            browser.close()
            return

        print("[*] Listening for messages...\n")

        last_msg = ""

        # --- MAIN LOOP ---
        while True:
            try:
                chat_messages = page.locator("div[dir='ltr']").all()
                if not chat_messages:
                    time.sleep(1)
                    continue

                latest = chat_messages[-1].inner_text().strip()

                if latest != last_msg:
                    print(f"[NEW MSG] {latest}")
                    last_msg = latest

                    reply = ask_llm(latest)
                    if reply:
                        print(f"[REPLY] {reply}")
                        input_box = page.locator("div[contenteditable='true']").last
                        input_box.fill(reply)
                        input_box.press("Enter")

            except Exception as e:
                print("[LOOP ERROR]", e)

            time.sleep(1)
