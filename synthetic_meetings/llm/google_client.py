from __future__ import annotations
import sys
from google import genai
from google.genai import types


def generate_ssml(api_key: str, system_prompt: str, user_prompt: str) -> str:
    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=8192,
            ),
        )
    except Exception as e:
        print(f"Error: Google AI Studio API call failed — {e}", file=sys.stderr)
        sys.exit(1)

    return response.text.strip()
