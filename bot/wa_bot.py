import time
import os
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

USER_DATA_DIR = "wa_user_data"
QR_PATH = "wa_qr.png"


# -------------------------------
# HELPERS
# -------------------------------
def capture_qr(page):
    """Screenshot QR when login is required."""
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR saved → {QR_PATH}")
    except Exception as e:
        print(f"[!] QR screenshot failed: {e}")


def is_logged_in(page):
    """Detect WhatsApp home screen."""
    try:
        return page.locator("//div[@role='textbox']").count() > 0
    except:
        return False


# -------------------------------
# GROUP FINDER
# -------------------------------
def open_group(page, group):
    print(f"[*] Searching group: {group}")

    # Try sidebar title match
    direct = page.locator(f"//span[@title='{group}']")
    if direct.count() > 0:
        direct.first.click()
        print(f"[+] Group opened: {group}")
        return True

    # Try search box
    try:
        search_box = page.locator("//div[@contenteditable='true']").nth(0)
        search_box.click()
        search_box.fill(group)
        time.sleep(2)

        result = page.locator(f"//span[@title='{group}']")
        if result.count() > 0:
            result.first.click()
            print(f"[+] Group opened via search: {group}")
            return True
    except Exception as e:
        print("[!] Search failed:", e)

    print(f"[!] Group not found: {group}")
    return False


# -------------------------------
# MESSAGE MONITORING
# -------------------------------
def listen(page, group):
    print(f"[+] Watching group → {group}")
    last = ""

    while True:
        try:
            msgs = page.locator("//div[contains(@class,'message-in')]").all()
            if not msgs:
                time.sleep(1)
                continue

            new_msg = msgs[-1].inner_text().strip()

            if new_msg != last:
                print(f"[NEW] {new_msg}")

                # Ask LLM only for non-English
                reply = ask_llm(new_msg)

                if reply:
                    print(f"[BOT] {reply}")
                    box = page.locator("//div[@contenteditable='true']").last
                    box.click()
                    box.fill(reply)
                    page.keyboard.press("Enter")

                last = new_msg

        except Exception as e:
            print("[!] Listener error:", e)

        time.sleep(1)


# -------------------------------
# MAIN BOT
# -------------------------------
def run_bot():
    print("[*] Starting WhatsApp bot...")

    chromium_path = "/opt/chrome/chrome"
    if not os.path.exists(chromium_path):
        raise FileNotFoundError("Chromium missing at /opt/chrome/chrome")

    with sync_playwright() as p:

        print("[*] Launching patched Chromium (stealth)...")

        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,
            executable_path=chromium_path,
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                "--disable-web-security",
                "--disable-site-isolation-trials",
                "--window-size=1366,768",
                "--hide-scrollbars",
                "--mute-audio",
            ],
        )

        page = browser.new_page()

        print("[*] Opening WhatsApp Web...")
        page.goto("https://web.whatsapp.com")

        # --------------------------------------------
        # LOGIN CHECK
        # --------------------------------------------
        print("[*] Checking login status...")

        if not is_logged_in(page):
            print("[!] Login required. QR will be generated...")
            capture_qr(page)

            waited = 0
            while waited < 180:
                if is_logged_in(page):
                    print("[+] Logged in successfully!")
                    break
                time.sleep(2)
                waited += 2

            if not is_logged_in(page):
                print("[X] Login failed after waiting.")
                browser.close()
                return
        else:
            print("[+] Logged in successfully!")

        # --------------------------------------------
        # GROUP OPEN
        # --------------------------------------------
        if not open_group(page, GROUP_NAME):
            print("[X] Cannot continue without opening the group.")
            browser.close()
            return

        # --------------------------------------------
        # START LISTENING
        # --------------------------------------------
        listen(page, GROUP_NAME)
