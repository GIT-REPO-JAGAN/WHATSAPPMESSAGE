import time
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

QR_PATH = "wa_qr.png"
USER_DATA_DIR = "wa_user_data"


# ---------------------------------------------------
# LOGIN CHECK + QR HANDLING
# ---------------------------------------------------
def ensure_logged_in(page):
    """Check if logged in; otherwise capture QR."""
    try:
        if page.locator("//div[@contenteditable='true']").count() > 0:
            return True
    except:
        pass

    # Capture QR screen
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR saved → {QR_PATH}")
    except Exception as e:
        print("[!] Failed to save QR:", e)

    return False


# ---------------------------------------------------
# FIND & OPEN GROUP
# ---------------------------------------------------
def find_and_open_group(page, group_name):
    print(f"[*] Searching for group: {group_name}")

    page.wait_for_selector("//div[@role='grid']", timeout=60000)

    # Search bar
    try:
        search_box = page.locator("//div[@contenteditable='true']").first
        search_box.click()
        time.sleep(1)
        search_box.fill(group_name)
        time.sleep(2)
    except Exception as e:
        print("[X] Search bar failed:", e)
        return False

    # Click group
    chat = page.locator(f"//span[@title='{group_name}']")
    if chat.count() > 0:
        chat.first.click()
        print(f"[+] Group '{group_name}' opened.")
        return True

    print(f"[!] Group '{group_name}' not found.")
    return False


# ---------------------------------------------------
# WATCH & RESPOND TO MESSAGES
# ---------------------------------------------------
def listen_for_messages(page, group_name):
    print(f"[+] Watching group '{group_name}'...")

    last_msg = ""

    while True:
        try:
            messages = page.locator(
                "//div[contains(@class,'message-in')]"
            ).all()

            if not messages:
                time.sleep(1)
                continue

            latest = messages[-1].inner_text().strip()

            if latest != last_msg:
                print(f"[NEW] → {latest}")

                reply = ask_llm(latest)

                if reply:
                    box = page.locator("//div[@contenteditable='true']").last
                    box.click()
                    box.fill(reply)
                    page.keyboard.press("Enter")

                    print(f"[BOT] → {reply}")

                last_msg = latest

        except Exception as e:
            print("[ERR] Listener error:", e)

        time.sleep(1)


# ---------------------------------------------------
# MAIN BOT
# ---------------------------------------------------
def run_bot():
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:

        print("[*] Launching real Google Chrome...")

        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            executable_path="/usr/bin/google-chrome",
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

        print("[*] Checking login status...")

        logged_in = ensure_logged_in(page)

        if not logged_in:
            print("[!] Scan the QR shown in wa_qr.png")
            MAX_WAIT = 180
            waited = 0

            while waited < MAX_WAIT:
                if page.locator("//div[@contenteditable='true']").count() > 0:
                    print("[+] Login successful!")
                    logged_in = True
                    break
                time.sleep(2)
                waited += 2

        if not logged_in:
            print("[X] Login failed after waiting.")
            return

        # OPEN GROUP
        if not find_and_open_group(page, GROUP_NAME):
            print("[X] Could not open group.")
            return

        # LISTEN FOR MESSAGES
        listen_for_messages(page, GROUP_NAME)
