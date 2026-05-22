from __future__ import annotations
import sys
from datetime import date
from pathlib import Path

from synthetic_meetings.ssml.parser import SpeakerTurn


def _make_output_dir(base_dir: Path, preset_name: str) -> Path:
    folder_name = f"{date.today().isoformat()}_{preset_name}"
    output_dir = base_dir / folder_name
    speakers_dir = output_dir / "speakers"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        speakers_dir.mkdir(exist_ok=True)
    except OSError as e:
        print(f"Error: could not create output directory — {e}", file=sys.stderr)
        sys.exit(1)

    return output_dir


def write_ssml(output_dir: Path, ssml: str) -> Path:
    path = output_dir / "meeting.ssml"
    path.write_text(ssml, encoding="utf-8")
    return path


def write_transcript(output_dir: Path, transcript: str) -> Path:
    path = output_dir / "transcript.txt"
    path.write_text(transcript, encoding="utf-8")
    return path


def write_speaker_wav(output_dir: Path, turn: SpeakerTurn, wav_bytes: bytes) -> Path:
    safe_name = turn.speaker_name.replace(" ", "_")
    filename = f"turn_{turn.index:03d}_{safe_name}.wav"
    path = output_dir / "speakers" / filename
    path.write_bytes(wav_bytes)
    return path


class Exporter:
    def __init__(self, base_dir: Path, preset_name: str):
        self.output_dir = _make_output_dir(base_dir, preset_name)
        self.speakers_dir = self.output_dir / "speakers"

    def save_ssml(self, ssml: str) -> Path:
        return write_ssml(self.output_dir, ssml)

    def save_transcript(self, transcript: str) -> Path:
        return write_transcript(self.output_dir, transcript)

    def save_speaker_wav(self, turn: SpeakerTurn, wav_bytes: bytes) -> Path:
        return write_speaker_wav(self.output_dir, turn, wav_bytes)

    def merged_wav_path(self) -> Path:
        return self.output_dir / "merged_meeting.wav"

    def merged_mp3_path(self) -> Path:
        return self.output_dir / "merged_meeting.mp3"

    def speaker_wav_paths(self) -> list[Path]:
        return sorted(self.speakers_dir.glob("turn_*.wav"))

    def summary(self) -> str:
        lines = [
            "",
            f"  Output directory : {self.output_dir}",
            f"  SSML             : {self.output_dir / 'meeting.ssml'}",
            f"  Transcript       : {self.output_dir / 'transcript.txt'}",
            f"  Speaker audio    : {self.speakers_dir}/",
            f"  Merged WAV       : {self.merged_wav_path()}",
            f"  Merged MP3       : {self.merged_mp3_path()}",
        ]
        return "\n".join(lines)
