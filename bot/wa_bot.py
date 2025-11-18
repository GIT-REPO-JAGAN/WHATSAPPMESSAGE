import time
import os
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

QR_PATH = "wa_qr.png"
USER_DATA_DIR = "wa_user_data"


def ensure_logged_and_capture_qr(page):
    """
    Checks if logged into WhatsApp.
    If not, capture QR screenshot.
    """

    try:
        # WhatsApp chat search bar loaded = logged in
        if page.locator("//div[@contenteditable='true']").count() > 0:
            return True
    except:
        pass

    # Capture QR screen
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR captured → {QR_PATH}")
    except Exception as e:
        print("[!] Could not capture QR:", e)

    return False


def find_and_open_group(page, group_name):
    """Find and open the target WhatsApp group."""
    page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)

    # Direct title match
    direct = page.locator(f'//span[@title="{group_name}"]')
    if direct.count() > 0:
        direct.first.click()
        print(f"[+] Group '{group_name}' opened.")
        return True

    # Fallback search
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
    """Watch the group for new incoming messages."""
    print(f"[+] Watching group '{group_name}'...")
    last_message = ""

    while True:
        try:
            messages = page.locator("//div[contains(@class,'message-in')]").all()
            if not messages:
                time.sleep(1)
                continue

            latest = messages[-1].inner_text().strip()
            if latest != last_message:
                print(f"[NEW MESSAGE] → {latest}")

                reply = ask_llm(latest)
                if reply:
                    print(f"[BOT REPLY] → {reply}")
                    box = page.locator("//div[@contenteditable='true']").last
                    box.click()
                    box.fill(reply)
                    page.keyboard.press("Enter")

                last_message = latest

        except Exception as e:
            print("[ERROR] Listener error:", e)

        time.sleep(1)


def run_bot():
    """Main function to start WhatsApp bot."""
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:

        # IMPORTANT — LAUNCH USING LATEST CHROME
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,
            executable_path="/opt/chrome/chrome",  # FIX FOR CHROME 85+ ERROR
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                "--disable-web-security",
                "--disable-site-isolation-trials",
                "--window-size=1366,768",
            ],
        )

        page = browser.new_page()
        page.goto("https://web.whatsapp.com")

        print("[*] Checking login status…")
        logged_in = ensure_logged_and_capture_qr(page)

        if not logged_in:
            print("[!] Login required — wa_qr.png generated")
            print("    → Open wa_qr.png")
            print("    → Scan using WhatsApp → Linked Devices")
            print("    → Waiting for login...")

        # Wait until WhatsApp loads fully
        MAX_WAIT = 180
        waited = 0

        while waited < MAX_WAIT:
            content = page.content()

            if "Search" in content or "search" in content.lower():
                print("[+] Login successful!")
                logged_in = True
                break

            if "End-to-end encrypted" in content:
                print("    → Syncing… please wait...")

            time.sleep(2)
            waited += 2

        if not logged_in:
            print("[X] Login timeout. Try again.")
            browser.close()
            return

        # Open group
        if not find_and_open_group(page, GROUP_NAME):
            print("[X] Cannot continue without target group.")
            browser.close()
            return

        # Start listening for messages
        listen_for_messages(page, GROUP_NAME)
