# WHATSAPPMESSAGE/bot/llm.py

import os
from openai import OpenAI
from .config import (
    TARGET_LANGUAGE,
    ENABLE_AI,
    DEBUG,
    OPENAI_MODEL,
    OPENAI_API_KEY
)

# OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)


def ask_llm(message: str):
    """
    Translate incoming WhatsApp messages into TARGET_LANGUAGE.

    Returns:
        - Translated text
        - None if:
            • AI disabled
            • Message already English → LLM returns EMPTY
            • LLM returns empty/none
            • Safety filters trigger
    """

    if not ENABLE_AI:
        return None

    try:
        if DEBUG:
            print(f"[LLM] Incoming: {message}")

        prompt = f"""
You are a translation and language-cleaning assistant for WhatsApp messages.

Rules:
- Translate the message into **{TARGET_LANGUAGE}**.
- If the message is already clear, proper English → return ONLY: EMPTY
- If message is abusive, explicit, hateful, dangerous, or illegal → return: "I cannot respond to that."
- Keep responses short and clean.

Message:
{message}
"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.2,
        )

        reply = response.choices[0].message["content"].strip()

        if DEBUG:
            print(f"[LLM] Raw reply: {reply}")

        # Conditions to skip translation
        if reply.lower() in ["", "none", "empty"]:
            return None

        return reply

    except Exception as e:
        print("[LLM ERROR]", e)
        return None
