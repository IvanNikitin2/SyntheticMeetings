from __future__ import annotations

from synthetic_meetings.ssml.parser import SpeakerTurn


def _format_timestamp(ms: int) -> str:
    total_seconds, millis = divmod(ms, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def build_vtt(turns: list[SpeakerTurn], durations_ms: list[int]) -> str:
    lines = ["WEBVTT", ""]

    position_ms = 0
    for turn, duration_ms in zip(turns, durations_ms):
        start = _format_timestamp(position_ms)
        end = _format_timestamp(position_ms + duration_ms)
        position_ms += duration_ms

        lines.append(f"{start} --> {end}")
        lines.append(f"{turn.label}: {turn.spoken_text}")
        lines.append("")

    return "\n".join(lines)


def build_speaker_vtt(
    turns: list[SpeakerTurn],
    durations_ms: list[int],
    voice_name: str,
) -> str:
    lines = ["WEBVTT", ""]

    position_ms = 0
    for turn, duration_ms in zip(turns, durations_ms):
        if turn.voice_name == voice_name:
            start = _format_timestamp(position_ms)
            end = _format_timestamp(position_ms + duration_ms)
            lines.append(f"{start} --> {end}")
            lines.append(f"{turn.label}: {turn.spoken_text}")
            lines.append("")
        position_ms += duration_ms

    return "\n".join(lines)
