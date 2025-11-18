# llm.py
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

import openai

# Read API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in .env file")

openai.api_key = OPENAI_API_KEY

def ask_llm(text: str) -> str:
    try:
        resp = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": text}],
            max_tokens=512,
            temperature=0.2,
        )
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[LLM error: {e}]"
