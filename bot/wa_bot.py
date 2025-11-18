import time
import os
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

QR_PATH = "wa_qr.png"
USER_DATA_DIR = "wa_user_data"


def ensure_logged_and_capture_qr(page):
    """
    Checks whether WhatsApp is logged in.
    If not, capture a QR code screenshot.
    """
    try:
        # If WhatsApp home UI is visible → logged in
        if page.locator("//div[@role='textbox']").count() > 0:
            return True

    except:
        pass

    # Take screenshot of QR page
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR captured successfully → {QR_PATH}")
    except Exception as e:
        print("[!] Failed to screenshot QR:", e)

    return False


def find_and_open_group(page, group_name):
    """
    Opens the specified WhatsApp group.
    """

    # Wait for chat list to load
    page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)

    # Try direct title match
    direct = page.locator(f'//span[@title="{group_name}"]')
    if direct.count() > 0:
        direct.first.click()
        print(f"[+] Group '{group_name}' opened.")
        return True

    # FALLBACK: Use search
    try:
        search = page.locator("//div[@contenteditable='true']").first
        search.click()
        search.fill(group_name)
        time.sleep(2)

        result = page.locator(f'//span[@title="{group_name}"]')
        if result.count() > 0:
            result.first.click()
            print(f"[+] Group '{group_name}' opened via search.")
            return True
    except:
        pass

    print(f"[!] Group '{group_name}' not found.")
    return False


def listen_for_messages(page, group_name):
    """
    Watches the group for new messages and replies if needed.
    """

    print(f"[+] Watching group '{group_name}'...")

    last_message = ""

    while True:
        try:
            # Most recent message div
            messages = page.locator("//div[contains(@class,'message-in')]").all()

            if not messages:
                time.sleep(2)
                continue

            latest = messages[-1].inner_text().strip()

            if latest != last_message:

                print(f"[NEW MESSAGE] → {latest}")

                reply = ask_llm(latest)

                if reply:
                    print(f"[BOT REPLY] → {reply}")

                    message_box = page.locator("//div[@contenteditable='true']").last
                    message_box.click()
                    message_box.fill(reply)
                    page.keyboard.press("Enter")

                last_message = latest

        except Exception as e:
            print("[ERROR] Message listener error:", e)

        time.sleep(1)


def run_bot():
    """
    Main bot runner for WhatsApp using Playwright.
    """

    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,  # use headless true (QR captures correctly)
            args=["--no-sandbox"],
        )

        page = browser.new_page()
        page.goto("https://web.whatsapp.com")

        print("[*] Checking login status…")

        logged_in = ensure_logged_and_capture_qr(page)

        MAX_WAIT = 180
        waited = 0

        if not logged_in:
            print("[!] Login required — QR saved as wa_qr.png")
            print("    → Open wa_qr.png")
            print("    → Scan QR using WhatsApp > Linked Devices")
            print("    → Waiting for login...")

        while waited < MAX_WAIT:
            content = page.content()

            if "Search" in content or "search" in content.lower():
                print("[+] Login successful!")
                logged_in = True
                break

            if "End-to-end encrypted" in content or "Loading" in content:
                print("    → Syncing… waiting...")

            time.sleep(2)
            waited += 2

        if not logged_in:
            print("[X] Login failed after waiting. Try scanning again.")
            browser.close()
            return

        # Open group
        if not find_and_open_group(page, GROUP_NAME):
            print("[X] Cannot continue without group.")
            browser.close()
            return

        # Start monitoring messages
        listen_for_messages(page, GROUP_NAME)

