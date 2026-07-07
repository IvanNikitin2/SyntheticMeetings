from __future__ import annotations
import io
import sys
from pathlib import Path

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub is not installed. Run: pip install pydub", file=sys.stderr)
    sys.exit(1)


def wav_bytes_to_segment(wav_bytes: bytes) -> AudioSegment:
    return AudioSegment.from_wav(io.BytesIO(wav_bytes))


def build_speaker_tracks(
    turns_with_audio: list[tuple[str, AudioSegment]],
) -> dict[str, AudioSegment]:
    total_ms = sum(seg.duration_seconds * 1000 for _, seg in turns_with_audio)
    total_ms = int(total_ms)

    voices = {voice for voice, _ in turns_with_audio}
    tracks: dict[str, AudioSegment] = {
        v: AudioSegment.silent(duration=total_ms) for v in voices
    }

    position_ms = 0
    for voice, seg in turns_with_audio:
        tracks[voice] = tracks[voice].overlay(seg, position=position_ms)
        position_ms += int(seg.duration_seconds * 1000)

    return tracks


def export_wav_mp3(combined: AudioSegment, output_wav: Path, output_mp3: Path) -> None:
    try:
        combined.export(str(output_wav), format="wav")
    except Exception as e:
        print(f"Error: failed to export WAV — {e}", file=sys.stderr)
        sys.exit(1)

    try:
        combined.export(str(output_mp3), format="mp3")
    except Exception as e:
        print(
            f"Error: failed to export MP3 — {e}\n"
            "Make sure ffmpeg is installed and available in your PATH.",
            file=sys.stderr,
        )
        sys.exit(1)


def merge_segments(segments: list[AudioSegment]) -> AudioSegment:
    if not segments:
        print("Error: no audio segments to merge.", file=sys.stderr)
        sys.exit(1)
    combined = AudioSegment.empty()
    for seg in segments:
        combined += seg
    return combined
