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
        # WhatsApp home screen → search box appears
        if page.locator("//div[@role='textbox']").count() > 0:
            return True
    except:
        pass

    # Save QR screen
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR captured → {QR_PATH}")
    except Exception as e:
        print(f"[!] QR capture error: {e}")

    return False


# ------------------------------------------------------
# GROUP FIND / OPEN
# ------------------------------------------------------
def find_and_open_group(page, group_name):

    page.wait_for_selector("div[aria-label='Chat list'], div[role='grid']", timeout=60000)

    # Direct title match
    direct = page.locator(f'//span[@title="{group_name}"]')
    if direct.count() > 0:
        direct.first.click()
        print(f"[+] Opened group: {group_name}")
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
            print(f"[+] Opened group via search: {group_name}")
            return True
    except:
        pass

    print(f"[!] Group not found: {group_name}")
    return False


# ------------------------------------------------------
# LISTEN FOR MESSAGES
# ------------------------------------------------------
def listen_for_messages(page, group_name):

    print(f"[+] Listening on group: {group_name}")
    last_message = ""

    while True:
        try:
            msgs = page.locator("//div[contains(@class,'message-in')]").all()

            if not msgs:
                time.sleep(1)
                continue

            latest = msgs[-1].inner_text().strip()

            if latest != last_message:
                print(f"[NEW MESSAGE] → {latest}")

                reply = ask_llm(latest)

                if reply:
                    print(f"[BOT] → {reply}")
                    box = page.locator("//div[@contenteditable='true']").last
                    box.click()
                    box.fill(reply)
                    page.keyboard.press("Enter")

                last_message = latest

        except Exception as e:
            print("[ERROR] in listener:", e)

        time.sleep(1)


# ------------------------------------------------------
# MAIN BOT RUNNER
# ------------------------------------------------------
def run_bot():

    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:

        print("[*] Launching Chromium...")

        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,  # IMPORTANT for server
            executable_path="/opt/chrome/chrome",
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                "--disable-web-security",
                "--window-size=1366,768",
                # REMOVED: "--remote-debugging-pipe"  (CAUSES ERROR)
            ],
        )

        page = browser.new_page()
        page.goto("https://web.whatsapp.com")

        print("[*] Checking login status...")

        logged_in = ensure_logged_and_capture_qr(page)

        if not logged_in:
            print("[!] Login required — wa_qr.png generated")
            print("    → Open wa_qr.png")
            print("    → Scan QR using WhatsApp → Linked Devices")
            print("    → Waiting for login...")

        # Wait for login
        MAX_WAIT = 180
        waited = 0

        while waited < MAX_WAIT:
            html = page.content()

            if "Search" in html or "search" in html.lower():
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
            print("[X] Cannot find group. Stopping.")
            browser.close()
            return

        # Start listener
        listen_for_messages(page, GROUP_NAME)
