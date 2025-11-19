import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ==============================
#  OPENAI CONFIG
# ==============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# ==============================
#  WHATSAPP BOT CONFIG
# ==============================
GROUP_NAME = os.getenv("GROUP_NAME", "").strip()
TARGET_LANGUAGE = os.getenv("TARGET_LANGUAGE", "English").strip()

# Enable / disable translation AI
ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"

# Detailed logging
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ==============================
#  LOGIN / BROWSER CONFIG
# ==============================
USE_PERSISTENT_LOGIN = os.getenv("USE_PERSISTENT_LOGIN", "true").lower() == "true"

PERSISTENT_DATA_DIR = os.getenv(
    "PERSISTENT_DATA_DIR",
    "/home/jaganath/WHATSAPPMESSAGE/wa_user_data"
).strip()

QR_CODE_PATH = os.getenv(
    "QR_CODE_PATH",
    "/home/jaganath/WHATSAPPMESSAGE/wa_qr.png"
).strip()

# ==============================
#  VALIDATION
# ==============================
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY missing in .env file.")

if not GROUP_NAME:
    raise ValueError("❌ GROUP_NAME missing in .env file.")

if DEBUG:
    print("=== CONFIG LOADED ===")
    print(f"Group: {GROUP_NAME}")
    print(f"Model: {OPENAI_MODEL}")
    print(f"AI Enabled: {ENABLE_AI}")
    print(f"Persistent Login: {USE_PERSISTENT_LOGIN}")
    print(f"Data Dir: {PERSISTENT_DATA_DIR}")
    print(f"QR Path: {QR_CODE_PATH}")
    print("======================")
