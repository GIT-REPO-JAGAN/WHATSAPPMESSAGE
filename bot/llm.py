import os
from dotenv import load_dotenv
from openai import OpenAI
from .config import TARGET_LANGUAGE, ENABLE_AI, DEBUG

# -----------------------------------------------------------
# ALWAYS load .env from ABSOLUTE PATH (systemd fix)
# -----------------------------------------------------------
ENV_PATH = "/home/jaganath/WHATSAPPMESSAGE/.env"
load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise ValueError(
        f"❌ OPENAI_API_KEY missing! Ensure it exists in {ENV_PATH}"
    )

# Initialize OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)


def ask_llm(message: str):
    """
    Convert the message into English.
    If already in English → bot returns None (no reply).
    If AI disabled → return None.
    """

    try:
        if DEBUG:
            print(f"[LLM] Incoming message: {message}")

        if not ENABLE_AI:
            return None

        prompt = f"""
You are a WhatsApp translation bot.
Convert the following message into {TARGET_LANGUAGE}.

Rules:
1. If the message is already proper English → reply EXACTLY: "##NO-REPLY##"
2. If the message is abusive, illegal, or harmful → reply: "I cannot respond to that."
3. Otherwise → return the corrected {TARGET_LANGUAGE} version.

Message:
{message}
"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.2,
        )

        reply = response.choices[0].message["content"].strip()

        if DEBUG:
            print(f"[LLM] Raw reply: {reply}")

        # No reply case
        if reply == "" or reply.lower() == "##no-reply##":
            return None

        return reply

    except Exception as e:
        print("[LLM ERROR]", e)
        return None
