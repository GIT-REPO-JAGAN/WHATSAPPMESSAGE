# WHATSAPPMESSAGE/bot/config.py
import os

# ---- WhatsApp Group Config ----
GROUP_NAME = os.getenv("GROUP_NAME", "TESTGROUP")   # Name of the group to monitor

# ---- AI / LLM Config ----
ENABLE_AI = os.getenv("ENABLE_AI", "1") == "1"      # Enable/disable LLM translation
TARGET_LANGUAGE = os.getenv("TARGET_LANGUAGE", "English")
DEBUG = os.getenv("DEBUG", "0") == "1"

# ---- Chrome executable (important for server) ----
# If you installed Google Chrome manually at /opt/chrome/chrome
CHROME_EXECUTABLE = os.getenv("CHROME_EXECUTABLE", "/opt/chrome/chrome")

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WA_USER_DATA = os.path.join(BASE_DIR, "wa_user_data")
QR_PATH = os.path.join(BASE_DIR, "wa_qr.png")

