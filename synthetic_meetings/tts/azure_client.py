from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path
import azure.cognitiveservices.speech as speechsdk


def _get_azure_config() -> tuple[str, str]:
    key = os.getenv("AZURE_TTS_KEY", "").strip()
    region = os.getenv("AZURE_TTS_REGION", "").strip()

    if not key:
        print("Error: AZURE_TTS_KEY is not set in your .env file.", file=sys.stderr)
        sys.exit(1)
    if not region:
        print("Error: AZURE_TTS_REGION is not set in your .env file.", file=sys.stderr)
        sys.exit(1)

    return key, region


def synthesize_turn(ssml_chunk: str, turn_index: int) -> bytes:
    key, region = _get_azure_config()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )

        audio_config = speechsdk.audio.AudioOutputConfig(filename=tmp_path)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        result = synthesizer.speak_ssml_async(ssml_chunk).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return Path(tmp_path).read_bytes()

        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            print(
                f"Error: Azure TTS failed at turn {turn_index} — {details.reason}: {details.error_details}",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"Error: Azure TTS returned unexpected result at turn {turn_index}.", file=sys.stderr)
        sys.exit(1)

    finally:
        Path(tmp_path).unlink(missing_ok=True)
