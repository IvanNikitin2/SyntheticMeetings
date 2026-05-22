from __future__ import annotations
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class SpeakerTurn:
    index: int
    voice_name: str
    speaker_name: str
    ssml_chunk: str
    plain_text: str


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


def _voice_to_ssml_chunk(voice_el: ET.Element, namespaces: dict[str, str]) -> str:
    ns_attrs = ""
    for prefix, uri in namespaces.items():
        if prefix == "":
            ns_attrs += f' xmlns="{uri}"'
        else:
            ns_attrs += f' xmlns:{prefix}="{uri}"'

    inner = ET.tostring(voice_el, encoding="unicode")
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"'
        f' xml:lang="en-US"{ns_attrs}>\n  {inner}\n</speak>'
    )


def _collect_namespaces(ssml: str) -> dict[str, str]:
    ns: dict[str, str] = {}
    for match in re.finditer(r'xmlns(?::(\w+))?="([^"]+)"', ssml):
        prefix = match.group(1) or ""
        uri = match.group(2)
        if uri != "http://www.w3.org/2001/10/synthesis":
            ns[prefix if prefix else "extra"] = uri
    return ns


def _resolve_speaker_name(voice_name: str, voice_name_map: dict[str, str]) -> str:
    return voice_name_map.get(voice_name, voice_name)


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

    extra_namespaces = _collect_namespaces(raw_ssml)

    for prefix, uri in re.findall(r'xmlns:?(\w*)="([^"]+)"', raw_ssml):
        ET.register_namespace(prefix or "", uri)
    ET.register_namespace("", "http://www.w3.org/2001/10/synthesis")

    try:
        root = ET.fromstring(raw_ssml)
    except ET.ParseError as e:
        print(f"Error: LLM returned invalid XML — {e}", file=sys.stderr)
        print("Raw output (first 500 chars):", file=sys.stderr)
        print(raw_ssml[:500], file=sys.stderr)
        sys.exit(1)

    local_name = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if local_name != "speak":
        print(f"Error: expected root element <speak>, got <{local_name}>.", file=sys.stderr)
        sys.exit(1)

    turns: list[SpeakerTurn] = []
    index = 1

    for child in root:
        child_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if child_local != "voice":
            continue

        voice_name = child.get("name", "")
        if not voice_name:
            print(f"Error: <voice> element at turn {index} is missing a 'name' attribute.", file=sys.stderr)
            sys.exit(1)

        ssml_chunk = _voice_to_ssml_chunk(child, extra_namespaces)
        inner_xml = ET.tostring(child, encoding="unicode")
        plain_text = _strip_tags(inner_xml)
        speaker_name = _resolve_speaker_name(voice_name, voice_name_map)

        turns.append(
            SpeakerTurn(
                index=index,
                voice_name=voice_name,
                speaker_name=speaker_name,
                ssml_chunk=ssml_chunk,
                plain_text=plain_text,
            )
        )
        index += 1

    if not turns:
        print("Error: SSML contains no <voice> elements.", file=sys.stderr)
        sys.exit(1)

    return turns


def derive_transcript(turns: list[SpeakerTurn]) -> str:
    lines = [f"[{t.speaker_name}]: {t.plain_text}" for t in turns]
    return "\n".join(lines)
