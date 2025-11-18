from openai import OpenAI
import re
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("LLM_API_KEY"))

def is_english(text):
    """
    Detect if text is English using a simple character heuristic.
    If the message is mostly composed of English letters and spaces,
    treat it as English.
    """
    english_ratio = len(re.findall(r"[A-Za-z ]", text)) / max(len(text), 1)
    return english_ratio > 0.65   # Adjust if needed

def ask_llm(message):
    """
    Respond ONLY if the message is NOT in English.
    Translate non-English messages into English.
    English messages → No reply (return None).
    """

    # Skip responding to English text
    if is_english(message):
        print("[INFO] English message detected → No reply needed.")
        return None

    # Translate to English using LLM
    prompt = f"Translate this to English in one short sentence: {message}"

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You translate messages into English."},
            {"role": "user", "content": prompt}
        ]
    )

    translated = response.choices[0].message["content"].strip()
    return translated
