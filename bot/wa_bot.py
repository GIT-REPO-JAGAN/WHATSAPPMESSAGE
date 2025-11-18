import time
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

QR_PATH = "wa_qr.png"
USER_DATA_DIR = "wa_user_data"


# ------------------------------------------------------
# LOGIN CHECK + QR CAPTURE
# ------------------------------------------------------
def ensure_logged_and_capture_qr(page):
    try:
        # WhatsApp home screen normally contains a searchable textbox
        if page.locator("//div[@role='textbox']").count() > 0:
            return True
    except:
        pass

    # Otherwise take screenshot of current page (QR)
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR captured successfully → {QR_PATH}")
    except Exception as e:
        print(f"[!] Could not capture QR: {e}")

    return False


# ------------------------------------------------------
# GROUP SEARCH / OPEN
# ------------------------------------------------------
def find_and_open_group(page, group_name):

    page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)

    # Direct match
    direct = page.locator(f'//span[@title="{group_name}"]')
    if direct.count() > 0:
        direct.first.click()
        print(f"[+] Group '{group_name}' opened.")
        return True

    # Fallback → Search bar
    try:
        search_box = page.locator("//div[@contenteditable='true']").first
        search_box.click()
        search_box.fill(group_name)
        time.sleep(2)

        result = page.locator(f'//span[@title="{group_name}"]')
        if result.count() > 0:
            result.first.click()
            print(f"[+] Group '{group_name}' opened via search.")
            return True
    except Exception:
        pass

    print(f"[!] Group '{group_name}' not found.")
    return False


# ------------------------------------------------------
# MESSAGE LISTENER LOOP
# ------------------------------------------------------
def listen_for_messages(page, group_name):

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
                    msg_box = page.locator("//div[@contenteditable='true']").last
                    msg_box.click()
                    msg_box.fill(reply)
                    page.keyboard.press("Enter")

                last_message = latest

        except Exception as e:
            print("[ERROR] Listener error:", e)

        time.sleep(1)


# ------------------------------------------------------
# MAIN BOT RUNNER
# ------------------------------------------------------
def run_bot():
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:

        print("[*] Launching Chromium (Playwright build)…")

        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,
            executable_path="/opt/chrome/chrome",   # IMPORTANT FIX
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                "--disable-web-security",
                "--disable-site-isolation-trials",
                "--window-size=1366,768",
                "--remote-debugging-pipe",
            ],
        )

        page = browser.new_page()
        page.goto("https://web.whatsapp.com")

        print("[*] Checking login status...")

        # Initial QR detection
        logged_in = ensure_logged_and_capture_qr(page)

        if not logged_in:
            print("[!] Login required — wa_qr.png generated")
            print("    → Open wa_qr.png")
            print("    → Scan using WhatsApp → Linked Devices")
            print("    → Waiting for login...")

        # Wait loop (up to 180 seconds)
        MAX_WAIT = 180
        waited = 0

        while waited < MAX_WAIT:
            content = page.content()

            # Detect WhatsApp logged in UI
            if "Search" in content or "search" in content.lower():
                print("[+] Login successful!")
                logged_in = True
                break

            time.sleep(2)
            waited += 2

        if not logged_in:
            print("[X] Login failed. Try scanning again.")
            browser.close()
            return

        # Open group
        if not find_and_open_group(page, GROUP_NAME):
            print("[X] Cannot continue without group.")
            browser.close()
            return

        # Begin listening
        listen_for_messages(page, GROUP_NAME)
