import time
import os
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

QR_PATH = "wa_qr.png"
USER_DATA_DIR = "wa_user_data"

# Path to Chrome-for-Testing
CHROME_EXECUTABLE = "/opt/chrome/chrome"


def ensure_logged_and_capture_qr(page):
    """
    Checks if WhatsApp is logged in.
    If NOT logged in → capture QR image.
    """
    try:
        # If search box exists → logged in
        if page.locator("//div[@role='textbox']").count() > 0:
            return True
    except:
        pass

    # Capture QR screenshot
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR captured → {QR_PATH}")
    except Exception as e:
        print("[!] Could not capture QR:", e)

    return False


def find_and_open_group(page, group_name):
    """
    Open WhatsApp group by name.
    """

    page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)

    # Direct match
    direct = page.locator(f'//span[@title="{group_name}"]')
    if direct.count() > 0:
        direct.first.click()
        print(f"[+] Group '{group_name}' opened.")
        return True

    # Search fallback
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

    except Exception as e:
        print("[ERROR] search:", e)

    print(f"[!] Group '{group_name}' NOT found.")
    return False


def listen_for_messages(page, group_name):
    """
    Watch group messages & respond.
    """

    print(f"[+] Watching group '{group_name}'...")

    last_msg = ""

    while True:
        try:
            msgs = page.locator("//div[contains(@class,'message-in')]").all()

            if not msgs:
                time.sleep(2)
                continue

            latest = msgs[-1].inner_text().strip()

            if latest != last_msg:

                print(f"[NEW] {latest}")

                reply = ask_llm(latest)

                if reply:
                    print(f"[BOT] {reply}")

                    box = page.locator("//div[@contenteditable='true']").last
                    box.click()
                    box.fill(reply)
                    page.keyboard.press("Enter")

                last_msg = latest

        except Exception as e:
            print("[ERROR] Listener:", e)

        time.sleep(1)


def run_bot():
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:

        # --------------------------------------------
        #   LAUNCH CHROME FOR TESTING (WhatsApp-safe)
        # --------------------------------------------
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,
            executable_path=CHROME_EXECUTABLE,
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

        MAX_WAIT = 200
        elapsed = 0

        if not logged_in:
            print("[!] Login required — wa_qr.png generated")
            print("    → Open wa_qr.png")
            print("    → Scan using WhatsApp → Linked Devices")
            print("    → Waiting for login...")

        # Wait for login and syncing
        while elapsed < MAX_WAIT:
            html = page.content()

            if "Search" in html or "search" in html.lower():
                print("[+] Login successful!")
                logged_in = True
                break

            if "End-to-end encrypted" in html or "Loading" in html:
                print("    → Syncing…")

            time.sleep(2)
            elapsed += 2

        if not logged_in:
            print("[X] Login failed. Rescan QR.")
            browser.close()
            return

        # open group
        if not find_and_open_group(page, GROUP_NAME):
            print("[X] Group not found. Stopping.")
            browser.close()
            return

        # start replying
        listen_for_messages(page, GROUP_NAME)
