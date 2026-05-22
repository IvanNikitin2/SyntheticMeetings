from __future__ import annotations
import sys
from openai import OpenAI, APIError


def _call(client: OpenAI, system: str, messages: list[dict]) -> tuple[str, str]:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4096,
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

    if context_tail:
        messages = [
            {"role": "user", "content": section_prompt},
            {"role": "assistant", "content": context_tail},
            {"role": "user", "content": "Continue writing the transcript from exactly where you stopped. Do not repeat anything already written. Do not add any heading or label."},
        ]
    else:
        messages = [{"role": "user", "content": section_prompt}]

    full_content = ""
    while True:
        content, finish_reason = _call(client, system_prompt, messages)
        full_content += content

        if finish_reason == "stop":
            break

        if finish_reason == "length":
            messages = messages + [
                {"role": "assistant", "content": full_content},
                {"role": "user", "content": "Continue the transcript from exactly where you stopped. Do not repeat anything. Do not add a heading."},
            ]
        else:
            break

    return full_content


def generate_ssml(api_key: str, system_prompt: str, user_prompt: str) -> str:
    return generate_section(api_key, system_prompt, user_prompt)
