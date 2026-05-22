from __future__ import annotations
import argparse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from synthetic_meetings.config.loader import load_preset
from synthetic_meetings.llm.provider import detect_provider
from synthetic_meetings.ssml.builder import build_system_prompt, build_section_prompts
from synthetic_meetings.ssml.assembler import assemble_ssml
from synthetic_meetings.ssml.parser import SpeakerTurn
from synthetic_meetings.tts.azure_client import synthesize_turn
from synthetic_meetings.audio.merger import merge_wav_files
from synthetic_meetings.exporter import Exporter

_CONTEXT_TAIL_CHARS = 1200


def _dialogue_to_transcript(raw_dialogue: str, valid_names: set[str]) -> str:
    lines = []
    for line in raw_dialogue.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        colon = stripped.find(":")
        if colon > 0 and stripped[:colon].strip() in valid_names:
            name = stripped[:colon].strip()
            text = stripped[colon + 1:].strip()
            lines.append(f"[{name}]: {text}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic meeting from a YAML preset."
    )
    parser.add_argument("preset", help="Path to the YAML preset file.")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Base output directory (default: ./output).",
    )
    args = parser.parse_args()

    print(f"Loading preset: {args.preset}")
    preset = load_preset(args.preset)

    print("Detecting LLM provider...")
    provider, api_key = detect_provider()
    print(f"Using LLM: {provider}")

    if provider == "anthropic":
        from synthetic_meetings.llm.claude_client import generate_section
    else:
        from synthetic_meetings.llm.openai_client import generate_section

    system_prompt = build_system_prompt(preset)
    sections = build_section_prompts(preset)

    print("Generating dialogue...")
    all_dialogue_parts: list[str] = []
    context_tail = ""

    for i, section in enumerate(sections, 1):
        print(f"  [{i}/{len(sections)}] {section.label}...", end=" ", flush=True)
        text = generate_section(api_key, system_prompt, section.prompt, context_tail)
        words = len(text.split())
        print(f"{words} words")
        all_dialogue_parts.append(text)
        context_tail = text[-_CONTEXT_TAIL_CHARS:]

    raw_dialogue = "\n".join(all_dialogue_parts)

    print("Assembling SSML...")
    full_ssml, ssml_turns = assemble_ssml(raw_dialogue, preset)
    print(f"  {len(ssml_turns)} speaker turns.")

    valid_names = {p.name for p in preset.participants}
    transcript = _dialogue_to_transcript(raw_dialogue, valid_names)

    exporter = Exporter(Path(args.output_dir), preset.name)

    print("Saving SSML and transcript...")
    exporter.save_ssml(full_ssml)
    exporter.save_transcript(transcript)

    print("Synthesizing audio via Azure TTS...")
    speaker_wav_paths = []
    for idx, (name, voice, ssml_chunk) in enumerate(ssml_turns, start=1):
        turn = SpeakerTurn(index=idx, voice_name=voice, speaker_name=name, ssml_chunk=ssml_chunk, plain_text="")
        print(f"  Turn {idx:03d} — {name} ({voice})")
        wav_bytes = synthesize_turn(ssml_chunk, idx)
        wav_path = exporter.save_speaker_wav(turn, wav_bytes)
        speaker_wav_paths.append(wav_path)

    print("Merging audio...")
    merge_wav_files(
        wav_paths=speaker_wav_paths,
        output_wav=exporter.merged_wav_path(),
        output_mp3=exporter.merged_mp3_path(),
    )

    print("\nDone.")
    print(exporter.summary())


if __name__ == "__main__":
    main()
