# WHATSAPPMESSAGE/bot/llm.py
import os
from groq import Groq
from .config import TARGET_LANGUAGE, ENABLE_AI, DEBUG

# Load Groq key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY missing! Set it in .env file.")

client = Groq(api_key=GROQ_API_KEY)


def ask_llm(message: str):
    """
    Translates any non-English WhatsApp message into TARGET_LANGUAGE using Groq.
    
    - If message is already English → return None
    - If message is abusive/illegal → return "I cannot respond to that."
    - Otherwise → return translated string
    """

    if not ENABLE_AI:
        return None

    try:
        if DEBUG:
            print(f"[LLM] Incoming: {message}")

        prompt = f"""
You are an AI assistant that translates WhatsApp messages into {TARGET_LANGUAGE}.

Rules:
- If the message is already proper English, return EMPTY.
- If the message contains abuse, hate speech, explicit content, or illegal material, return: "I cannot respond to that."
- Otherwise, translate it naturally and clearly.

Message:
{message}
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.2,
        )

        reply = response.choices[0].message["content"].strip()

        if DEBUG:
            print(f"[LLM] Raw reply: {reply}")

        # These values mean "no translation needed"
        if reply.lower() in ["", "empty", "none"]:
            return None

        return reply

    except Exception as e:
        print("[LLM ERROR]", e)
        return None
