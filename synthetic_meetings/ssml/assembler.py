from __future__ import annotations
import re
import sys
import xml.sax.saxutils as saxutils
from synthetic_meetings.config.models import MeetingPreset, Participant


_RATE_MAP = {"slow": "slow", "medium": "medium", "fast": "fast"}
_PITCH_MAP = {"low": "low", "default": "medium", "high": "high"}


def _build_name_to_participant(preset: MeetingPreset) -> dict[str, Participant]:
    return {p.name.lower(): p for p in preset.participants}


def _escape(text: str) -> str:
    return saxutils.escape(text)


def _wrap_in_voice(text: str, participant: Participant) -> str:
    escaped = _escape(text.strip())

    inner = escaped
    if participant.speaking_rate or participant.pitch:
        rate = _RATE_MAP.get(participant.speaking_rate or "medium", "medium")
        pitch = _PITCH_MAP.get(participant.pitch or "default", "medium")
        inner = f'<prosody rate="{rate}" pitch="{pitch}">{inner}</prosody>'

    return f'  <voice name="{participant.voice}">\n    {inner}\n  </voice>'


def _parse_dialogue_lines(raw: str, name_to_participant: dict[str, Participant]) -> list[tuple[Participant, str]]:
    turns: list[tuple[Participant, str]] = []
    current_participant: Participant | None = None
    current_lines: list[str] = []

    for line in raw.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("//"):
            continue

        colon_pos = stripped.find(":")
        if colon_pos > 0:
            possible_name = stripped[:colon_pos].strip().lower()
            if possible_name in name_to_participant:
                if current_participant and current_lines:
                    turns.append((current_participant, " ".join(current_lines)))
                current_participant = name_to_participant[possible_name]
                current_lines = [stripped[colon_pos + 1:].strip()]
                continue

        if current_participant:
            current_lines.append(stripped)

    if current_participant and current_lines:
        turns.append((current_participant, " ".join(current_lines)))

    return turns


def _needs_msspeech_ns(preset: MeetingPreset) -> bool:
    return any(p.style for p in preset.participants)


def assemble_ssml(raw_dialogue: str, preset: MeetingPreset) -> tuple[str, list[tuple[str, str, str]]]:
    name_to_participant = _build_name_to_participant(preset)
    turns = _parse_dialogue_lines(raw_dialogue, name_to_participant)

    if not turns:
        print("Error: could not parse any speaker turns from LLM dialogue output.", file=sys.stderr)
        print("First 300 chars of output:", file=sys.stderr)
        print(raw_dialogue[:300], file=sys.stderr)
        sys.exit(1)

    ns_extra = ' xmlns:msspeech="http://www.microsoft.com/speech/synthesis"' if _needs_msspeech_ns(preset) else ""

    voice_blocks = []
    ssml_turns: list[tuple[str, str, str]] = []

    for idx, (participant, text) in enumerate(turns, start=1):
        voice_block = _wrap_in_voice(text, participant)
        voice_blocks.append(voice_block)

        per_speaker_ssml = (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"'
            f' xml:lang="en-US"{ns_extra}>\n'
            f'{voice_block}\n'
            f'</speak>'
        )
        ssml_turns.append((participant.name, participant.voice, per_speaker_ssml))

    full_ssml = (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"'
        f' xml:lang="en-US"{ns_extra}>\n'
        + "\n".join(voice_blocks)
        + "\n</speak>"
    )

    return full_ssml, ssml_turns
