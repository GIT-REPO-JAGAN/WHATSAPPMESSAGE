import time
import os
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

QR_PATH = "wa_qr.png"
USER_DATA_DIR = "wa_user_data"


def ensure_logged_and_capture_qr(page):
    """
    Checks whether WhatsApp web is logged in.
    If not, capture a QR code for login.
    """
    try:
        # If WhatsApp chat UI is visible => logged in
        if page.locator("//div[@role='textbox']").count() > 0:
            return True
    except:
        pass

    # Capture QR
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR captured successfully → {QR_PATH}")
    except Exception as e:
        print("[!] Failed to screenshot QR:", e)

    return False


def find_and_open_group(page, group_name):
    """
    Opens the specified WhatsApp group chat.
    """

    print(f"[*] Looking for group '{group_name}'...")

    page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)

    # Direct match first
    direct = page.locator(f'//span[@title="{group_name}"]')
    if direct.count() > 0:
        direct.first.click()
        print(f"[+] Group '{group_name}' opened.")
        return True

    # Fallback: search
    try:
        print("[*] Searching for group by name...")
        search_box = page.locator("//div[@contenteditable='true']").first
        search_box.click()
        search_box.fill(group_name)
        time.sleep(2)

        result = page.locator(f'//span[@title="{group_name}"]')
        if result.count() > 0:
            result.first.click()
            print(f"[+] Group '{group_name}' opened via search.")
            return True
    except Exception as e:
        print("[!] Search failed:", e)

    print(f"[!] Group '{group_name}' not found.")
    return False


def listen_for_messages(page, group_name):
    """
    Continuously monitors group messages and replies using LLM.
    """
    print(f"[+] Watching group '{group_name}'...\n")

    last_message = ""

    while True:
        try:
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

                    msg_box = page.locator("//div[@contenteditable='true']").last
                    msg_box.click()
                    msg_box.fill(reply)
                    page.keyboard.press("Enter")

                last_message = latest

        except Exception as e:
            print("[ERROR] Message listener error:", e)

        time.sleep(1)


def run_bot():
    """
    Main WhatsApp bot execution logic.
    """

    print("[*] Starting WhatsApp bot...\n")

    with sync_playwright() as p:

        # -----------------------------------------------------------
        # PLAYWRIGHT BROWSER FIX — WORKS WITH WHATSAPP 2025+
        # -----------------------------------------------------------
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-background-networking",
            ],
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
            print("    → Waiting for login...\n")

        while waited < MAX_WAIT:
            content = page.content()

            # Detect login success
            if (
                "Search or start new chat" in content
                or "search" in content.lower()
                or page.locator("//div[@role='textbox']").count() > 0
            ):
                print("[+] Login successful!\n")
                logged_in = True
                break

            # Syncing stage
            if "End-to-end encrypted" in content or "Loading" in content:
                print("    → Syncing… waiting...")

            time.sleep(2)
            waited += 2

        if not logged_in:
            print("[X] Login failed after waiting. Try scanning again.")
            browser.close()
            return

        # -----------------------------------------------------------
        # Open target group
        # -----------------------------------------------------------
        if not find_and_open_group(page, GROUP_NAME):
            print("[X] Cannot continue without group.")
            browser.close()
            return

        # -----------------------------------------------------------
        # Start listening
        # -----------------------------------------------------------
        listen_for_messages(page, GROUP_NAME)
