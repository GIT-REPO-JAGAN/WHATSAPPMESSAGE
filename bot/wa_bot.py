import os
import time
import pathlib
import traceback
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from .llm import ask_llm
from .config import GROUP_NAME, DEBUG, ENABLE_AI, CHROME_EXECUTABLE

ROOT = pathlib.Path(__file__).resolve().parents[1]
QR_PATH = str(ROOT / "wa_qr.png")
USER_DATA_DIR = str(ROOT / "wa_user_data")

DEFAULT_VIEWPORT = {"width": 1600, "height": 1200}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def log(*args):
    if DEBUG:
        print("[DEBUG]", *args)
    else:
        print(*args)


def ensure_dir_permissions():
    try:
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        os.chmod(USER_DATA_DIR, 0o700)
    except Exception as e:
        print("[WARN] Could not ensure wa_user_data permissions:", e)


def capture_qr(page):
    try:
        page.screenshot(path=QR_PATH, full_page=True)
        os.chmod(QR_PATH, 0o644)
        print(f"[+] QR saved → {QR_PATH}")
        return True
    except Exception as e:
        print("[!] Failed saving QR:", e)
        return False


def is_logged_in(page):
    try:
        content = page.content().lower()
        if "search" in content or "chats" in content:
            return True
        if page.locator('//div[@role="textbox"]').count() > 0:
            return True
    except:
        pass
    return False


def wait_for_login(page, max_wait=180):
    if is_logged_in(page):
        print("[+] Already logged in.")
        return True

    print("[!] Login required — generating QR...")
    capture_qr(page)

    waited = 0
    while waited < max_wait:
        if is_logged_in(page):
            print("[+] Login successful!")
            return True
        time.sleep(2)
        waited += 2

    print("[X] Login timeout.")
    return False


def find_search_box(page):
    selectors = [
        "//div[@contenteditable='true' and @role='textbox']",
        "//div[@contenteditable='true' and @data-tab]",
        "//div[@contenteditable='true']",
    ]

    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=8000)
            return loc
        except:
            continue

    return None


def open_group(page, group_name):
    try:
        el = page.locator(f'//span[@title="{group_name}"]')
        if el.count() > 0:
            el.first.click()
            log(f"[+] Opened group (direct): {group_name}")
            return True
    except:
        pass

    search = find_search_box(page)
    if not search:
        print("[ERROR] Search box not found!")
        return False

    try:
        search.click()
        search.fill(group_name)
        time.sleep(1.5)

        el = page.locator(f'//span[@title="{group_name}"]')
        if el.count() > 0:
            el.first.click()
            log(f"[+] Opened group (via search): {group_name}")
            return True
    except Exception as e:
        log("[WARN] group search failed:", e)

    print(f"[X] Group not found: {group_name}")
    return False


def get_latest_message_text(page):
    selectors = [
        "//div[contains(@class,'message-in')]//span[contains(@class,'selectable-text')]",
        "//div[contains(@class,'message-in')]//span[@dir='ltr']",
    ]

    for sel in selectors:
        try:
            msgs = page.locator(sel).all()
            if msgs:
                return msgs[-1].inner_text().strip()
        except:
            pass

    return None


def listen_and_translate(page, group_name):
    print(f"[+] Listening in → {group_name}")
    last_msg = None

    while True:
        try:
            msg = get_latest_message_text(page)
            if not msg or msg == last_msg:
                time.sleep(1)
                continue

            print("[NEW]", msg)
            last_msg = msg

            translation = ask_llm(msg)
            if translation:
                print("[SEND]", translation)

                try:
                    box = page.locator("//div[@contenteditable='true' and @data-tab]").last
                    box.click()
                    box.fill(translation)
                    page.keyboard.press("Enter")
                except Exception as e:
                    print("[SEND ERROR]", e)
            else:
                print("[>] No translation needed.")

        except Exception as e:
            print("[ERROR] Listener:", e)
            traceback.print_exc()
            time.sleep(2)


def run_bot():
    print("[*] Starting WhatsApp bot...")
    ensure_dir_permissions()

    with sync_playwright() as p:
        launch_args = [
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-site-isolation-trials",
            "--window-size=1600,1200",
            "--headless=new",
        ]

        try:
            browser = p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=True,
                args=launch_args,
                viewport=DEFAULT_VIEWPORT,
                user_agent=DEFAULT_USER_AGENT,
                **({"executable_path": CHROME_EXECUTABLE} if CHROME_EXECUTABLE else {})
            )
        except Exception as e:
            print("[ERROR] Browser launch failed:", e)
            return

        page = browser.new_page()
        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        if not wait_for_login(page):
            browser.close()
            return

        if not open_group(page, GROUP_NAME):
            browser.close()
            return

        listen_and_translate(page, GROUP_NAME)


if __name__ == "__main__":
    run_bot()
