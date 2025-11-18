import os
import time
from playwright.sync_api import sync_playwright
from .llm import ask_llm
from .config import GROUP_NAME

QR_PATH = "wa_qr.png"
USER_DATA_DIR = "/home/jaganath/WHATSAPPMESSAGE/wa_user_data"


def run_bot():
    print("[*] Starting WhatsApp bot...")

    with sync_playwright() as p:

        print("[*] Launching patched Chromium (stealth mode)...")

        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=True,
            executable_path="/opt/chrome/chrome",
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                "--disable-web-security",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1366,768",
                "--disable-infobars",
                "--disable-notifications",
                "--disable-popup-blocking"
            ],
        )

        page = browser.new_page()

        # -----------------------------
        # 1. SPOOF USER AGENT (REAL CHROME 120)
        # -----------------------------
        fake_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.6099.129 Safari/537.36"
        )

        page.set_extra_http_headers({"User-Agent": fake_agent})

        # Apply user agent to Playwright context
        page.evaluate(f"""
            Object.defineProperty(navigator, 'userAgent', {{
                get: () => "{fake_agent}"
            }});
        """)

        # -----------------------------
        # 2. REMOVE HEADLESS DETECTION
        # -----------------------------
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });

            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter){
                if (parameter === 37445) return 'NVIDIA Corporation';
                if (parameter === 37446) return 'GeForce GTX 1080/PCIe/SSE2';
                return getParameter(parameter);
            };

            window.chrome = {
                runtime: {},
                app: {},
            };
        """)

        # -----------------------------
        # 3. OPEN WHATSAPP WEB
        # -----------------------------
        print("[*] Opening WhatsApp Web...")
        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        # -----------------------------
        # 4. WAIT FOR QR OR MAIN UI
        # -----------------------------
        print("[*] Checking login status...")

        for _ in range(60):
            html = page.content()

            if "Scan this QR code" in html or "Use WhatsApp" in html:
                try:
                    page.screenshot(path=QR_PATH, full_page=True)
                    print(f"[!] QR generated → {QR_PATH}")
                except:
                    print("[!] QR screenshot failed (permission?)")
                break

            if "Search" in html or "Chats" in html:
                print("[+] Logged in successfully!")
                break

            time.sleep(2)

        # -----------------------------
        # 5. OPEN GROUP
        # -----------------------------
        print("[*] Searching for group:", GROUP_NAME)

        search_box = page.locator("//div[@contenteditable='true']").first
        search_box.click()
        search_box.fill(GROUP_NAME)
        time.sleep(2)

        group = page.locator(f"//span[@title='{GROUP_NAME}']")

        if group.count() == 0:
            print("[X] Group not found!")
            return

        group.first.click()
        print("[+] Group opened!")

        # -----------------------------
        # 6. LISTEN FOR MESSAGES
        # -----------------------------
        last_message = ""

        print("[*] Bot is now active...")

        while True:
            try:
                msgs = page.locator("//div[contains(@class,'message-in')]").all()

                if not msgs:
                    time.sleep(2)
                    continue

                latest = msgs[-1].inner_text().strip()

                if latest != last_message:
                    print("[NEW]", latest)

                    reply = ask_llm(latest)

                    if reply:
                        box = page.locator("//div[@contenteditable='true']").last
                        box.click()
                        box.fill(reply)
                        page.keyboard.press("Enter")

                    last_message = latest

            except Exception as e:
                print("[!] Listener error:", e)

            time.sleep(1)

