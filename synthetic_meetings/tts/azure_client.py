from __future__ import annotations
import os
import sys
import struct
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


def _build_wav_header(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(pcm_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_data


def synthesize_turn(ssml_chunk: str, turn_index: int) -> bytes:
    key, region = _get_azure_config()

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)

    # Raw16Khz16BitMonoPcm: uncompressed raw PCM — no codec, no audio device pipeline
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw24Khz16BitMonoPcm
    )

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_ssml_async(ssml_chunk).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return _build_wav_header(result.audio_data, sample_rate=24000)

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        print(
            f"Error: Azure TTS failed at turn {turn_index} — {details.reason}: {details.error_details}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Error: Azure TTS returned unexpected result at turn {turn_index}.", file=sys.stderr)
    sys.exit(1)
