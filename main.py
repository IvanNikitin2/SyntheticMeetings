from __future__ import annotations
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from synthetic_meetings.ssml.parser import parse_ssml, derive_transcript
from synthetic_meetings.tts.azure_client import synthesize_turn
from synthetic_meetings.audio.merger import merge_wav_files
from synthetic_meetings.exporter import Exporter


def _process_ssml_file(ssml_path: Path, output_base: Path) -> None:
    print(f"\nProcessing: {ssml_path.name}")

    raw_ssml = ssml_path.read_text(encoding="utf-8")
    turns = parse_ssml(raw_ssml, {})

    print(f"  {len(turns)} speaker turns parsed.")

    meeting_name = ssml_path.stem
    exporter = Exporter(output_base, meeting_name)

    exporter.save_ssml(raw_ssml)
    exporter.save_transcript(derive_transcript(turns))

    print("  Synthesizing audio via Azure TTS...")
    speaker_wav_paths = []
    for turn in turns:
        print(f"    Turn {turn.index:03d} — {turn.speaker_name} ({turn.voice_name})")
        wav_bytes = synthesize_turn(turn.ssml_chunk, turn.index)
        wav_path = exporter.save_speaker_wav(turn, wav_bytes)
        speaker_wav_paths.append(wav_path)

    print("  Merging audio...")
    merge_wav_files(
        wav_paths=speaker_wav_paths,
        output_wav=exporter.merged_wav_path(),
        output_mp3=exporter.merged_mp3_path(),
    )

    print("  Done.")
    print(exporter.summary())


def main() -> None:
    input_dir = Path("input")

    if len(sys.argv) > 1:
        targets = [Path(p) for p in sys.argv[1:]]
    else:
        if not input_dir.exists():
            print(f"Error: '{input_dir}' folder not found. Create it and add .ssml files.", file=sys.stderr)
            sys.exit(1)
        targets = sorted(input_dir.glob("*.ssml"))
        if not targets:
            print(f"Error: no .ssml files found in '{input_dir}/'.", file=sys.stderr)
            sys.exit(1)

    for path in targets:
        if not path.exists():
            print(f"Error: file not found — {path}", file=sys.stderr)
            sys.exit(1)
        if path.suffix.lower() != ".ssml":
            print(f"Error: expected an .ssml file, got — {path}", file=sys.stderr)
            sys.exit(1)

    output_base = Path("output")

    for ssml_path in targets:
        _process_ssml_file(ssml_path, output_base)


if __name__ == "__main__":
    main()
