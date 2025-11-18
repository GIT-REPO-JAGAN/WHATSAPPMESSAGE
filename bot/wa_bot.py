with sync_playwright() as p:

    print("[*] Launching Chrome 1194 (latest) ...")

    browser = p.chromium.launch_persistent_context(
        USER_DATA_DIR,
        headless=True,
        executable_path="/opt/chrome/chrome",   # IMPORTANT: USE OUR CUSTOM CHROME
        args=[
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-software-rasterizer",
            "--disable-web-security",
            "--disable-site-isolation-trials",
            "--window-size=1366,768",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--disable-translate",
            "--disable-popup-blocking",
            "--hide-scrollbars",
            "--mute-audio",
            "--remote-debugging-pipe",
        ],
    )
