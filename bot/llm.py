# WHATSAPPMESSAGE/bot/llm.py
import os
from groq import Groq
from .config import TARGET_LANGUAGE, ENABLE_AI, DEBUG, GROQ_API_KEY, MODEL

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY missing! Set it inside .env.")

client = Groq(api_key=GROQ_API_KEY)


def ask_llm(message: str):
    """
    Translate incoming message into English using Groq LLaMA 3.1.
    Returns:
        - translation text
        - None if no translation needed
    """

    if not ENABLE_AI:
        if DEBUG:
            print("[LLM] AI disabled, skipping.")
        return None

    try:
        if DEBUG:
            print(f"[LLM] Incoming message: {message}")

        prompt = f"""
You are a translation bot for WhatsApp.
Translate the following message into {TARGET_LANGUAGE}.

Rules:
- If the message is already good English, return EMPTY.
- If the message is abusive, illegal, explicit, hateful or unsafe, return: "I cannot respond to that."
- Keep only the translated sentence. No explanations.

Message:
{message}
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.3,
        )

        reply = response.choices[0].message["content"].strip()

        if DEBUG:
            print(f"[LLM] Raw reply: {reply}")

        # Means “don’t send”
        if reply.lower() in ["", "empty", "none"]:
            return None

        return reply

    except Exception as e:
        print("[LLM ERROR]", e)
        return None
