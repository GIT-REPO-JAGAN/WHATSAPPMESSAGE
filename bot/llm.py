# WHATSAPPMESSAGE/bot/llm.py
import os
from openai import OpenAI
from .config import TARGET_LANGUAGE, ENABLE_AI, DEBUG

# Load from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY missing! Set it in .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

def ask_llm(message: str):
    """
    Translate message into TARGET_LANGUAGE using LLM.
    Return None if:
     - AI disabled
     - Message already English or LLM returned EMPTY/None
    """

    if not ENABLE_AI:
        return None

    try:
        if DEBUG:
            print(f"[LLM] Incoming: {message}")

        prompt = f"""
You are a translation assistant for WhatsApp messages.
Your task:
- Translate the message into {TARGET_LANGUAGE}.
- If the message is already good English, return EMPTY (no output).
- If the message is abusive, hateful, explicit, or illegal, return: "I cannot respond to that."

Message:
{message}
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.2
        )

        reply = response.choices[0].message["content"].strip()

        if DEBUG:
            print(f"[LLM] Raw reply: {reply}")

        if reply.lower() in ["", "none", "empty"]:
            return None

        return reply

    except Exception as e:
        print("[LLM ERROR]", e)
        return None
