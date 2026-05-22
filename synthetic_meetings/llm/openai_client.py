from __future__ import annotations
import sys
from openai import OpenAI, APIError

_TOKENS_PER_SECTION = 1500
_MAX_CONTINUATIONS = 2


def _call(client: OpenAI, system: str, messages: list[dict]) -> tuple[str, str]:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=_TOKENS_PER_SECTION,
            temperature=0.85,
            frequency_penalty=0.3,
            messages=[{"role": "system", "content": system}] + messages,
        )
    except APIError as e:
        print(f"Error: OpenAI API call failed — {e}", file=sys.stderr)
        sys.exit(1)

    choice = response.choices[0]
    return choice.message.content, choice.finish_reason


def generate_section(api_key: str, system_prompt: str, section_prompt: str, context_tail: str = "") -> str:
    client = OpenAI(api_key=api_key)

    messages = [{"role": "user", "content": section_prompt}]
    if context_tail:
        messages = [
            {"role": "user", "content": section_prompt},
            {"role": "assistant", "content": context_tail},
            {"role": "user", "content": "Continue the transcript from exactly where you stopped. Do not repeat anything already written. Do not add any heading or label."},
        ]

    full_content = ""
    continuations = 0
    while True:
        content, finish_reason = _call(client, system_prompt, messages)
        full_content += content

        if finish_reason == "stop" or continuations >= _MAX_CONTINUATIONS:
            break

        if finish_reason == "length":
            continuations += 1
            tail = full_content[-800:]
            messages = [
                {"role": "user", "content": section_prompt},
                {"role": "assistant", "content": tail},
                {"role": "user", "content": "Continue the transcript from exactly where you stopped. Do not repeat anything. Do not add a heading."},
            ]
        else:
            break

    return full_content


def generate_ssml(api_key: str, system_prompt: str, user_prompt: str) -> str:
    return generate_section(api_key, system_prompt, user_prompt)
