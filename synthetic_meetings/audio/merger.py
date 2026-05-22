from __future__ import annotations
import io
import sys
from pathlib import Path

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub is not installed. Run: pip install pydub", file=sys.stderr)
    sys.exit(1)


def merge_wav_files(wav_paths: list[Path], output_wav: Path, output_mp3: Path) -> None:
    if not wav_paths:
        print("Error: no WAV files to merge.", file=sys.stderr)
        sys.exit(1)

    combined = AudioSegment.empty()
    for wav_path in wav_paths:
        try:
            segment = AudioSegment.from_wav(str(wav_path))
        except Exception as e:
            print(f"Error: failed to load {wav_path} — {e}", file=sys.stderr)
            sys.exit(1)
        combined += segment

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


def wav_bytes_to_segment(wav_bytes: bytes) -> AudioSegment:
    return AudioSegment.from_wav(io.BytesIO(wav_bytes))
