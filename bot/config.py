# WHATSAPPMESSAGE/bot/config.py
import os

# Load environment variables
GROUP_NAME = os.getenv("GROUP_NAME", "TESTGROUP")

# GROQ settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Enable / disable AI
ENABLE_AI = int(os.getenv("ENABLE_AI", "1")) == 1

# Debug mode
DEBUG = int(os.getenv("DEBUG", "0")) == 1

# Chrome path (optional, otherwise Playwright default Chromium is used)
CHROME_EXECUTABLE = os.getenv("CHROME_EXECUTABLE", None)

# Target output language for translation
TARGET_LANGUAGE = "English"
