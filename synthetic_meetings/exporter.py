from __future__ import annotations
import sys
from datetime import date
from pathlib import Path

from pydub import AudioSegment

from synthetic_meetings.ssml.parser import SpeakerTurn


def _make_output_dir(base_dir: Path, meeting_name: str) -> Path:
    folder_name = f"{date.today().isoformat()}_{meeting_name}"
    output_dir = base_dir / folder_name
    speakers_dir = output_dir / "speakers"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        speakers_dir.mkdir(exist_ok=True)
    except OSError as e:
        print(f"Error: could not create output directory — {e}", file=sys.stderr)
        sys.exit(1)

    return output_dir


def _safe_voice_label(voice_name: str) -> str:
    return voice_name.replace("-", "_").replace(" ", "_")


class Exporter:
    def __init__(self, base_dir: Path, meeting_name: str):
        self.output_dir = _make_output_dir(base_dir, meeting_name)
        self.speakers_dir = self.output_dir / "speakers"
        self._speaker_paths: list[Path] = []

    def save_ssml(self, ssml: str) -> Path:
        path = self.output_dir / "meeting.ssml"
        path.write_text(ssml, encoding="utf-8")
        return path

    def save_transcript(self, transcript: str) -> Path:
        path = self.output_dir / "transcript.txt"
        path.write_text(transcript, encoding="utf-8")
        return path

    def save_speaker_track(
        self,
        index: int,
        voice_name: str,
        track: AudioSegment,
        ssml: str,
    ) -> Path:
        label = _safe_voice_label(voice_name)
        wav_path = self.speakers_dir / f"speaker_{index}_{label}.wav"
        ssml_path = self.speakers_dir / f"speaker_{index}_{label}.ssml"

        try:
            track.export(str(wav_path), format="wav")
        except Exception as e:
            print(f"Error: failed to export {wav_path} — {e}", file=sys.stderr)
            sys.exit(1)

        ssml_path.write_text(ssml, encoding="utf-8")
        self._speaker_paths.append(wav_path)
        return wav_path

    def merged_wav_path(self) -> Path:
        return self.output_dir / "merged_meeting.wav"

    def merged_mp3_path(self) -> Path:
        return self.output_dir / "merged_meeting.mp3"

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
