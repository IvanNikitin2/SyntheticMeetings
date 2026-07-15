from __future__ import annotations
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass

_SYNTH_NS = "http://www.w3.org/2001/10/synthesis"


@dataclass
class SpeakerTurn:
    index: int
    voice_name: str
    speaker_name: str
    ssml_chunk: str
    plain_text: str
    label: str
    spoken_text: str


_LABEL_RE = re.compile(r"^([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){0,3}):\s+(.*)$", re.DOTALL)


def _split_label(plain_text: str, fallback: str) -> tuple[str, str]:
    m = _LABEL_RE.match(plain_text.strip())
    if m and len(m.group(1)) <= 40:
        return m.group(1).strip(), m.group(2).strip()
    return fallback, plain_text.strip()


def _strip_tags(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    clean = (
        clean.replace("&amp;", "&")
             .replace("&lt;", "<")
             .replace("&gt;", ">")
             .replace("&apos;", "'")
             .replace("&quot;", '"')
    )
    return clean


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _find_voices_with_prosody(
    element: ET.Element,
    inherited_prosody: list[dict[str, str]],
) -> list[tuple[ET.Element, list[dict[str, str]]]]:
    found: list[tuple[ET.Element, list[dict[str, str]]]] = []
    for child in element:
        tag = _local(child.tag)
        if tag == "voice":
            found.append((child, inherited_prosody))
        elif tag == "prosody":
            attrs = {k: v for k, v in child.attrib.items()}
            found.extend(_find_voices_with_prosody(child, inherited_prosody + [attrs]))
        else:
            found.extend(_find_voices_with_prosody(child, inherited_prosody))
    return found


def _strip_label_from_element(element: ET.Element, label: str) -> None:
    prefix = f"{label}:"
    for node in element.iter():
        if node.text and node.text.strip():
            stripped = node.text.lstrip()
            if stripped.startswith(prefix):
                remainder = stripped[len(prefix):]
                node.text = remainder.lstrip() if remainder.strip() else " "
            return


def _voice_to_ssml_chunk(voice_el: ET.Element, prosody_stack: list[dict[str, str]]) -> str:
    inner = ET.tostring(voice_el, encoding="unicode").strip()

    for attrs in reversed(prosody_stack):
        attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        voice_name = voice_el.get("name", "")
        open_tag = f'<voice name="{voice_name}">'
        close_tag = "</voice>"
        body = inner[len(_voice_open_tag(inner)):].rsplit(close_tag, 1)[0]
        inner = f'{open_tag}<prosody {attr_str}>{body}</prosody>{close_tag}'

    return (
        f'<speak version="1.0" xmlns="{_SYNTH_NS}" xml:lang="en-US">\n  {inner}\n</speak>'
    )


def _voice_open_tag(voice_xml: str) -> str:
    return voice_xml[:voice_xml.index(">") + 1]


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end]).strip()
    return text


def parse_ssml(raw_ssml: str, voice_name_map: dict[str, str]) -> list[SpeakerTurn]:
    raw_ssml = _strip_markdown_fences(raw_ssml)

    ET.register_namespace("", _SYNTH_NS)

    try:
        root = ET.fromstring(raw_ssml)
    except ET.ParseError as e:
        print(f"Error: SSML file has invalid XML — {e}", file=sys.stderr)
        print("Raw output (first 500 chars):", file=sys.stderr)
        print(raw_ssml[:500], file=sys.stderr)
        sys.exit(1)

    if _local(root.tag) != "speak":
        print(f"Error: expected root element <speak>, got <{_local(root.tag)}>.", file=sys.stderr)
        sys.exit(1)

    voices = _find_voices_with_prosody(root, [])

    turns: list[SpeakerTurn] = []
    for index, (voice_el, prosody_stack) in enumerate(voices, start=1):
        voice_name = voice_el.get("name", "")
        if not voice_name:
            print(f"Error: <voice> element at turn {index} is missing a 'name' attribute.", file=sys.stderr)
            sys.exit(1)

        plain_text = _strip_tags(ET.tostring(voice_el, encoding="unicode"))
        speaker_name = voice_name_map.get(voice_name, voice_name)
        label, spoken_text = _split_label(plain_text, speaker_name)

        if label != speaker_name or plain_text.strip().startswith(f"{label}:"):
            _strip_label_from_element(voice_el, label)

        ssml_chunk = _voice_to_ssml_chunk(voice_el, prosody_stack)

        turns.append(
            SpeakerTurn(
                index=index,
                voice_name=voice_name,
                speaker_name=speaker_name,
                ssml_chunk=ssml_chunk,
                plain_text=plain_text,
                label=label,
                spoken_text=spoken_text,
            )
        )

    if not turns:
        print("Error: SSML contains no <voice> elements.", file=sys.stderr)
        sys.exit(1)

    return turns


def derive_transcript(turns: list[SpeakerTurn]) -> str:
    lines = [f"[{t.speaker_name}]: {t.plain_text}" for t in turns]
    return "\n".join(lines)
