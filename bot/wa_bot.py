# WHATSAPPMESSAGE/bot/wa_bot.py
import os
import time
import pathlib
import traceback
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from .llm import ask_llm
from .config import GROUP_NAME, DEBUG, ENABLE_AI, CHROME_EXECUTABLE

# files / folders
ROOT = pathlib.Path(__file__).resolve().parents[1]
QR_PATH = str(ROOT / "wa_qr.png")
USER_DATA_DIR = str(ROOT / "wa_user_data")

# recommended values (can override in config.py)
DEFAULT_VIEWPORT = {"width": 1600, "height": 1200}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def log(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)
    else:
        print(*args, **kwargs)


def ensure_dir_permissions():
    """
    Make sure user data dir exists and is writable by the running user.
    """
    try:
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        # ensure readable/writable
        os.chmod(USER_DATA_DIR, 0o700)
    except Exception as e:
        print("[WARN] Could not ensure wa_user_data permissions:", e)


def capture_qr(page):
    """
    Save a screenshot (full page) so QR can be scanned.
    Returns True when saved.
    """
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        print(f"[+] QR saved → {QR_PATH}")
        # ensure file permission so systemd user (same user) can access it
        try:
            os.chmod(QR_PATH, 0o644)
        except Exception:
            pass
        return True
    except Exception as e:
        print("[!] Could not capture QR:", e)
        return False


def is_logged_in(page):
    """
    Detect a logged-in / WhatsApp main UI state.
    Multiple heuristics: presence of search or chat list, textbox role etc.
    """
    try:
        content = page.content().lower()
        # typical logged-in strings:
        if "search or start new chat" in content or "chats" in content or "search" in content:
            return True
        # direct element presence
        if page.locator('//div[@role="textbox"]').count() > 0:
            return True
    except Exception:
        pass
    return False


def wait_for_login(page, max_wait=180):
    """
    If not logged in, capture QR and wait for login for `max_wait` seconds.
    """
    if is_logged_in(page):
        print("[+] Already logged in.")
        return True

    print("[!] Login required — generating QR (wa_qr.png)")
    capture_qr(page)

    waited = 0
    interval = 2
    while waited < max_wait:
        try:
            if is_logged_in(page):
                print("[+] Login successful!")
                return True
        except Exception:
            pass
        time.sleep(interval)
        waited += interval

    print("[X] Login failed (timeout).")
    return False


def find_search_box(page, timeout=20):
    """
    Robustly find the search / chat search input using multiple selectors.
    Returns the Locator or raises.
    """
    selectors = [
        "//div[@contenteditable='true' and @role='textbox']",
        "//div[contains(@class,'copyable-text') and @contenteditable='true']",
        "//div[@contenteditable='true']",
        "//div[@data-tab='3' and @contenteditable='true']",
        "//div[@title='Search input textbox']",
    ]

    for sel in selectors:
        try:
            loc = page.locator(sel).first
            # wait small time for it to be visible/attached
            loc.wait_for(state="visible", timeout=timeout * 1000)
            return loc
        except PWTimeout:
            continue
        except Exception:
            continue

    raise RuntimeError("Search box not found")


def open_group(page, group_name):
    """
    Open the specific group by title or by search fallback.
    """
    # try direct click by group title
    try:
        el = page.locator(f'//span[@title="{group_name}"]')
        if el.count() > 0:
            el.first.click()
            log(f"[+] Opened group '{group_name}' (direct).")
            return True
    except Exception:
        pass

    # fallback: use search box
    try:
        search = find_search_box(page, timeout=10)
        search.click()
        search.fill(group_name)
        time.sleep(1.5)
        el = page.locator(f'//span[@title="{group_name}"]')
        if el.count() > 0:
            el.first.click()
            log(f"[+] Opened group '{group_name}' (via search).")
            return True
    except Exception as e:
        log("[WARN] open_group fallback failed:", e)

    print(f"[X] Group '{group_name}' not found.")
    return False


def get_latest_message_text(page):
    """
    Tries common message-in selectors and returns last message text.
    """
    try:
        # vary selectors for different WhatsApp DOMs
        msg_locators = [
            "//div[contains(@class,'message-in')]//span[contains(@class,'selectable-text')]",
            "//div[contains(@class,'_1wlJG')]//span[contains(@class,'selectable-text')]",
            "//div[contains(@class,'message-in')]//div[@dir='ltr']",
            "//div[contains(@class,'message-in')]//span[@dir='ltr']",
        ]

        for sel in msg_locators:
            messages = page.locator(sel).all()
            if messages:
                text = messages[-1].inner_text().strip()
                return text
    except Exception:
        pass
    return None


def listen_and_translate(page, group_name):
    """
    Monitor chat and convert non-English messages to English using ask_llm.
    If the LLM returns None/empty → no reply (means message already English or skipped).
    """
    print(f"[+] Watching '{group_name}' for incoming messages...")
    last_text = None
    while True:
        try:
            latest = get_latest_message_text(page)
            if not latest:
                time.sleep(1)
                continue

            if latest != last_text:
                print("[NEW]", latest)
                # call LLM to translate (ask_llm should return None for already-English)
                translation = ask_llm(latest)
                if translation:
                    print("[TRANSLATION]", translation)
                    # put translation back in input box (but as per your choice, you said "for English word no reaction" — we only post when LLM returns text)
                    try:
                        message_box = page.locator("//div[@contenteditable='true' and @data-tab]").last
                        message_box.click()
                        message_box.fill(translation)
                        page.keyboard.press("Enter")
                        print("[+] Sent translation to group.")
                    except Exception as e:
                        print("[!] Failed to send translation:", e)
                else:
                    print("[>] No reply needed (already English / skipped).")

                last_text = latest

        except Exception as e:
            print("[ERROR] listener:", e)
            traceback.print_exc()
            time.sleep(2)


def run_bot():
    print("[*] Starting WhatsApp bot...")
    ensure_dir_permissions()

    with sync_playwright() as p:
        # browser args force desktop layout so WhatsApp shows search bar in headless mode:
        launch_args = [
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-site-isolation-trials",
            "--disable-software-rasterizer",
            "--disable-web-security",
            "--force-device-scale-factor=1",
            "--high-dpi-support=1",
            "--window-size=1600,1200",
            "--headless=new",  # use new headless mode that supports rendering
        ]

        try:
            print("[*] Launching Chromium (Playwright build)...")
            browser = p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=True,
                args=launch_args,
                viewport=DEFAULT_VIEWPORT,
                user_agent=DEFAULT_USER_AGENT,
                # if you installed chrome at /opt/chrome/chrome, play with executable_path
                **({"executable_path": CHROME_EXECUTABLE} if CHROME_EXECUTABLE else {}),
            )
        except Exception as e:
            print("[!] Failed launching chromium:", e)
            traceback.print_exc()
            return

        page = browser.new_page()
        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        # LOGIN
        if not wait_for_login(page, max_wait=180):
            print("[X] Could not login - closing.")
            try:
                browser.close()
            except Exception:
                pass
            return

        # OPEN GROUP
        if not open_group(page, GROUP_NAME):
            print("[X] Cannot open group. Closing.")
            browser.close()
            return

        # START LISTENER
        listen_and_translate(page, GROUP_NAME)


if __name__ == "__main__":
    run_bot()
