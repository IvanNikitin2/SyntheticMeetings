from __future__ import annotations
import os
import sys


def detect_provider() -> tuple[str, str]:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if anthropic_key:
        return "anthropic", anthropic_key
    if openai_key:
        return "openai", openai_key

    print(
        "Error: no LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file.",
        file=sys.stderr,
    )
    sys.exit(1)
