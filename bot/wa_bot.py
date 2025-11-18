import time
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

QR_PATH = "wa_qr.png"
USER_DATA_DIR = "wa_user_data"


# ------------------------------------------------------
# CHECK LOGIN + QR CAPTURE
# ------------------------------------------------------
def ensure_logged_and_capture_qr(page):

    try:
        # Search bar exists → logged in
        if page.locator("//div[@role='textbox']").count() > 0:
            return True
    except:
        pass

    # Not logged in → capture QR
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR captured → {QR_PATH}")
    except Exception as e:
        print("[!] Failed to capture QR:", e)

    return False


# ------------------------------------------------------
# OPEN WHATSAPP GROUP
# ------------------------------------------------------
def find_and_open_group(page, group_name):

    # Wait for chat list
    page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)

    # Try direct match
    direct = page.locator(f'//span[@title="{group_name}"]')
    if direct.count() > 0:
        direct.first.click()
        print(f"[+] Group '{group_name}' opened.")
        return True

    # Search method
    try:
        search = page.locator("//div[@contenteditable='true']").first
        search.click()
        search.fill(group_name)
        time.sleep(1.5)

        result = page.locator(f'//span[@title="{group_name}"]')
        if result.count() > 0:
            result.first.click()
            print(f"[+] Group '{group_name}' opened via search.")
            return True
    except Exception as e:
        print("[ERROR] Search failed:", e)

    print(f"[!] Group '{group_name}' not found.")
    return False


# ------------------------------------------------------
# LISTEN & REPLY TO MESSAGES
# ------------------------------------------------------
def listen_for_messages(page, group_name):

    print(f"[+] Listening for messages in '{group_name}'...")
    last_message = ""

    while True:
        try:
            # Get incoming messages
            messages = page.locator("//div[contains(@class,'message-in')]").all()

            if not messages:
                time.sleep(1)
                continue

            latest = messages[-1].inner_text().strip()

            # Only act on NEW messages
            if latest != last_message:
                print(f"[NEW MESSAGE] → {latest}")

                translation = ask_llm(latest)

                if translation:
                    print(f"[BOT REPLY] → {translation}")

                    message_box = page.locator("//div[@contenteditable='true']").last
                    message_box.click()
                    message_box.fill(translation)
                    page.keyboard.press("Enter")

                last_message = latest

        except Exception as e:
            print("[ERROR] Listener crashed:", e)

        time.sleep(1)


# ------------------------------------------------------
# MAIN BOT FUNCTION
# ------------------------------------------------------
def run_bot():

    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:

        # FIXED → headless=True to avoid XServer error
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,               # REQUIRED on VPS
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
            ],
        )

        page = browser.new_page()
        page.goto("https://web.whatsapp.com")

        print("[*] Checking login status...")

        logged_in = ensure_logged_and_capture_qr(page)

        MAX_WAIT = 180
        waited = 0

        if not logged_in:
            print("[!] Scan QR from wa_qr.png (Stored in Project Folder)")
            print("[!] Waiting for login...")

        # Waiting Loop
        while waited < MAX_WAIT:
            html = page.content()

            if "Search" in html or "search" in html.lower():
                print("[+] Login successful!")
                logged_in = True
                break

            time.sleep(2)
            waited += 2

        if not logged_in:
            print("[X] Login failed. Try again.")
            browser.close()
            return

        # Open group
        if not find_and_open_group(page, GROUP_NAME):
            print("[X] Cannot open group. Exiting.")
            browser.close()
            return

        # Start message loop
        listen_for_messages(page, GROUP_NAME)
