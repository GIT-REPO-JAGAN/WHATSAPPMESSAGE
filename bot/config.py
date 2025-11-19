# WHATSAPPMESSAGE/bot/config.py

import os

# Group the bot should join/watch
GROUP_NAME = os.getenv("GROUP_NAME", "TESTGROUP")

# Target language the LLM should convert to (the user asked "convert to English")
TARGET_LANGUAGE = os.getenv("TARGET_LANGUAGE", "English")

# Toggle AI responses
ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() in ("1", "true", "yes")

# Debug prints
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

# Optional explicit chrome executable (if you installed Chrome to non-default location)
# Example: "/opt/chrome/chrome"
CHROME_EXECUTABLE = os.getenv("CHROME_EXECUTABLE", "") or None
