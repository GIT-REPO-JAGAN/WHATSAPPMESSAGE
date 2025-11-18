import os
from openai import OpenAI
from .config import TARGET_LANGUAGE, ENABLE_AI, DEBUG

# Load from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY missing! Set it before running WhatsApp bot.")

client = OpenAI(api_key=OPENAI_API_KEY)


def ask_llm(message: str):
    """
    Convert any message to English.
    Skip reply if the message is already English or if AI is disabled.
    """

    try:
        if DEBUG:
            print(f"[LLM] Incoming message: {message}")

        if not ENABLE_AI:
            return None

        prompt = f"""
You are a WhatsApp translation bot.
Convert the following message into {TARGET_LANGUAGE}.
If the message is already perfect English, return an empty string.
If the message is abusive, illegal, or harmful, return: "I cannot respond to that."

Message:
{message}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.2,
        )

        reply = response.choices[0].message["content"].strip()

        if DEBUG:
            print(f"[LLM] Raw reply: {reply}")

        # If empty = don’t send back
        if reply == "" or reply.lower() == "none":
            return None

        return reply

    except Exception as e:
        print("[LLM ERROR]", e)
        return None
