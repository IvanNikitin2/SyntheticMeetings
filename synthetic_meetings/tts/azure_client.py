from __future__ import annotations
import os
import sys
import time
import urllib.request
import urllib.error


_TTS_URL = "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
_TOKEN_URL = "https://{region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
_MAX_RETRIES = 3


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
    url = _TTS_URL.format(region=region)

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
        "User-Agent": "SyntheticMeetings",
    }

    body = ssml_chunk.encode("utf-8")

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            if e.code == 429 and attempt < _MAX_RETRIES:
                time.sleep(4 * attempt)
                continue
            print(
                f"Error: Azure TTS HTTP {e.code} at turn {turn_index} — {error_body}",
                file=sys.stderr,
            )
            sys.exit(1)
        except urllib.error.URLError as e:
            if attempt < _MAX_RETRIES:
                time.sleep(2 * attempt)
                continue
            print(
                f"Error: Azure TTS connection failed at turn {turn_index} — {e.reason}",
                file=sys.stderr,
            )
            sys.exit(1)
        except TimeoutError:
            if attempt < _MAX_RETRIES:
                time.sleep(2 * attempt)
                continue
            print(
                f"Error: Azure TTS timed out at turn {turn_index}.",
                file=sys.stderr,
            )
            sys.exit(1)

    sys.exit(1)
