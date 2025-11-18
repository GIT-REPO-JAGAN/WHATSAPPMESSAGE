import time
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

QR_PATH = "wa_qr.png"
USER_DATA_DIR = "wa_user_data"


# ------------------------------------------------------
#  LOGIN CHECK + QR CAPTURE
# ------------------------------------------------------
def ensure_logged_and_capture_qr(page):
    """
    Checks if WhatsApp is logged in.
    If not logged in, screenshot the QR page.
    """

    try:
        # If search box exists, user is logged in
        if page.locator("//div[@role='textbox']").count() > 0:
            return True

    except:
        pass

    # Not logged in → capture QR
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR captured successfully → {QR_PATH}")

    except Exception as e:
        print("[!] Failed to capture QR:", e)

    return False


# ------------------------------------------------------
#  OPEN GROUP
# ------------------------------------------------------
def find_and_open_group(page, group_name):
    """
    Finds and opens the specified WhatsApp group.
    """

    # Wait for chat UI
    page.wait_for_selector('div[role="grid"], div[aria-label="Chat list"]', timeout=60000)

    # Try direct match
    direct = page.locator(f'//span[@title="{group_name}"]')
    if direct.count() > 0:
        direct.first.click()
        print(f"[+] Group '{group_name}' opened.")
        return True

    # Fallback: Search bar
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
#  MESSAGE LISTENER
# ------------------------------------------------------
def listen_for_messages(page, group_name):
    """
    Watches the group for new incoming messages
    and replies only if translation is needed.
    """

    print(f"[+] Watching group '{group_name}'...")

    last_message = ""

    while True:
        try:
            messages = page.locator("//div[contains(@class,'message-in')]").all()

            if not messages:
                time.sleep(1)
                continue

            latest = messages[-1].inner_text().strip()

            # Only act on new messages
            if latest != last_message:
                print(f"[NEW MESSAGE] → {latest}")

                # Use LLM to translate if not English
                reply = ask_llm(latest)

                if reply and reply != latest:
                    print(f"[BOT REPLY] → {reply}")

                    message_box = page.locator("//div[@contenteditable='true']").last
                    message_box.click()
                    message_box.fill(reply)
                    page.keyboard.press("Enter")

                last_message = latest

        except Exception as e:
            print("[ERROR] Message listener crashed:", e)

        time.sleep(1)


# ------------------------------------------------------
#  MAIN BOT RUNNER
# ------------------------------------------------------
def run_bot():
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:

        # IMPORTANT — run non-headless to avoid Chrome 85+ error
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,  # FIX: required for WhatsApp Web
            args=["--no-sandbox", "--disable-gpu"],
        )

        page = browser.new_page()
        page.goto("https://web.whatsapp.com")

        print("[*] Checking login status...")

        logged_in = ensure_logged_and_capture_qr(page)

        MAX_WAIT = 180
        waited = 0

        if not logged_in:
            print("[!] Login required — QR saved as wa_qr.png")
            print("    → Open wa_qr.png")
            print("    → Scan using WhatsApp → Linked Devices")
            print("    → Waiting for login...")

        # Wait for login
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
            print("[X] Cannot continue without group.")
            browser.close()
            return

        # Start monitoring
        listen_for_messages(page, GROUP_NAME)
