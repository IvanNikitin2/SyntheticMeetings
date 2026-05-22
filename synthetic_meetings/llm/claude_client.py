from __future__ import annotations
import sys
import anthropic


def _call(client: anthropic.Anthropic, system: str, messages: list[dict]) -> tuple[str, str]:
    try:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=system,
            messages=messages,
        )
    except anthropic.APIError as e:
        print(f"Error: Anthropic API call failed — {e}", file=sys.stderr)
        sys.exit(1)

    stop_reason = response.stop_reason
    content = response.content[0].text
    return content, stop_reason


def generate_section(api_key: str, system_prompt: str, section_prompt: str, context_tail: str = "") -> str:
    client = anthropic.Anthropic(api_key=api_key)

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
        content, stop_reason = _call(client, system_prompt, messages)
        full_content += content

        if stop_reason == "end_turn":
            break

        if stop_reason == "max_tokens":
            messages = messages + [
                {"role": "assistant", "content": full_content},
                {"role": "user", "content": "Continue the transcript from exactly where you stopped. Do not repeat anything. Do not add a heading."},
            ]
        else:
            break

    return full_content


def generate_ssml(api_key: str, system_prompt: str, user_prompt: str) -> str:
    return generate_section(api_key, system_prompt, user_prompt)
