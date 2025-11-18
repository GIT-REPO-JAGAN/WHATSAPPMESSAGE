import os
import time
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME, DEBUG, ENABLE_AI

USER_DATA = os.path.join(os.getcwd(), "wa_user_data")
QR_FILE = os.path.join(os.getcwd(), "wa_qr.png")


def debug_print(msg):
    if DEBUG:
        print(msg)


def wait_for_qr(page):
    """Extract QR code and save as PNG."""
    try:
        qr_element = page.locator("canvas").first
        qr_element.screenshot(path=QR_FILE)
        print(f"[+] QR saved → {QR_FILE}")
    except Exception as e:
        print("[!] Could not capture QR:", e)


def ensure_logged_in(page):
    """
    Ensures user is logged in.
    If not logged in, generates QR and waits.
    """
    debug_print("[*] Checking login status...")

    # WhatsApp shows canvas QR when logged out
    try:
        qr_visible = page.locator("canvas").first.is_visible(timeout=5000)
    except:
        qr_visible = False

    if qr_visible:
        print("[!] Login required. QR will be generated...")
        wait_for_qr(page)
        print("[*] Waiting for login...")

        # Wait for WhatsApp to load after scanning
        page.wait_for_selector("text=Search or start new chat", timeout=0)
        print("[+] Logged in successfully!")
    else:
        print("[+] Logged in successfully!")


def open_group(page):
    """Open the target group chat."""
    print(f"[*] Searching for group: {GROUP_NAME}")

    try:
        search_box = page.locator("//div[@contenteditable='true']").first
        search_box.click()
        search_box.fill(GROUP_NAME)
    except Exception as e:
        print("[ERROR] Search box not found:", e)
        return False

    # Click the group name
    try:
        page.locator(f"text={GROUP_NAME}").first.click()
        print(f"[+] Group opened: {GROUP_NAME}")
        return True
    except Exception:
        print("[!] Group not found. Check GROUP_NAME in config.")
        return False


def listen_for_messages(page):
    """Listen for new incoming WhatsApp messages."""
    print("[*] Listening for new messages...")

    last_msg = ""

    while True:
        try:
            messages = page.locator("span.selectable-text").all()

            if not messages:
                time.sleep(1)
                continue

            latest = messages[-1].inner_text().strip()

            if latest != last_msg:
                last_msg = latest
                print(f"[NEW MESSAGE] {latest}")

                if ENABLE_AI:
                    response = ask_llm(latest)
                    if response:
                        send_message(page, response)

        except Exception as e:
            print("[ERROR] Message listener crashed:", e)

        time.sleep(1)


def send_message(page, text):
    """Send a message to the group."""
    try:
        message_box = page.locator("//div[@contenteditable='true']").last
        message_box.fill(text)
        message_box.press("Enter")
        print(f"[SENT] {text}")
    except Exception as e:
        print("[SEND ERROR]", e)


def launch_browser(p):
    """Launch Chrome in TRUE headless mode — required for systemd."""
    print("[*] Launching real Google Chrome (headless)...")

    return p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA,
        executable_path="/usr/bin/google-chrome",
        headless=True,  # CRITICAL FIX — MUST BE TRUE IN SYSTEMD
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


def run_bot():
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()

        page.goto("https://web.whatsapp.com")

        ensure_logged_in(page)
        if open_group(page):
            listen_for_messages(page)

        browser.close()
