from __future__ import annotations
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from synthetic_meetings.ssml.parser import parse_ssml, derive_transcript, SpeakerTurn
from synthetic_meetings.ssml.vtt import build_vtt, build_speaker_vtt
from synthetic_meetings.tts.azure_client import synthesize_turn
from synthetic_meetings.audio.merger import wav_bytes_to_segment, build_speaker_tracks, merge_segments, export_wav_mp3
from synthetic_meetings.exporter import Exporter


def _build_speaker_ssml(voice_name: str, turns: list[SpeakerTurn]) -> str:
    blocks = []
    for t in turns:
        ssml = t.ssml_chunk.strip()
        start = ssml.index(">") + 1
        end = ssml.rindex("</speak>")
        blocks.append(ssml[start:end].strip())
    inner = "\n  ".join(blocks)
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">\n'
        f'  {inner}\n'
        f'</speak>'
    )


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
    turns_with_audio: list[tuple[str, object]] = []
    durations_ms: list[int] = []
    for turn in turns:
        print(f"    Turn {turn.index:03d} — {turn.voice_name}")
        if turn.index > 1:
            # Pace requests so Azure TTS doesn't throttle and drop connections
            # mid-response (seen as IncompleteRead on rapid back-to-back turns).
            time.sleep(0.8)
        wav_bytes = synthesize_turn(turn.ssml_chunk, turn.index)
        seg = wav_bytes_to_segment(wav_bytes)
        turns_with_audio.append((turn.voice_name, seg))
        durations_ms.append(int(seg.duration_seconds * 1000))

    print("  Writing VTT...")
    exporter.save_vtt(build_vtt(turns, durations_ms))

    print("  Building speaker tracks...")
    speaker_tracks = build_speaker_tracks(turns_with_audio)

    voice_to_turns: dict[str, list[SpeakerTurn]] = {}
    for turn in turns:
        voice_to_turns.setdefault(turn.voice_name, []).append(turn)

    for idx, (voice_name, track) in enumerate(sorted(speaker_tracks.items()), start=1):
        speaker_ssml = _build_speaker_ssml(voice_name, voice_to_turns[voice_name])
        speaker_vtt = build_speaker_vtt(turns, durations_ms, voice_name)
        exporter.save_speaker_track(idx, voice_name, track, speaker_ssml, speaker_vtt)
        print(f"    Speaker {idx}: {voice_name}")

    print("  Merging audio...")
    segments = [seg for _, seg in turns_with_audio]
    combined = merge_segments(segments)
    export_wav_mp3(combined, exporter.merged_wav_path(), exporter.merged_mp3_path())

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

    failures = []
    for ssml_path in targets:
        try:
            _process_ssml_file(ssml_path, output_base)
        except SystemExit:
            # One file failing (e.g. Azure dropped a connection) shouldn't
            # abort the whole batch — log it and continue with the rest.
            print(f"  Skipped {ssml_path.name} due to an error above.", file=sys.stderr)
            failures.append(ssml_path.name)

    if failures:
        print(f"\nCompleted with {len(failures)} failed file(s): {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
