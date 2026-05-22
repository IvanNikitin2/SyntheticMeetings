from __future__ import annotations
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from synthetic_meetings.config.models import MeetingPreset, PresetFile


def load_preset(path: str | Path) -> MeetingPreset:
    preset_path = Path(path)
    if not preset_path.exists():
        print(f"Error: preset file not found: {preset_path}", file=sys.stderr)
        sys.exit(1)

    with preset_path.open("r", encoding="utf-8") as f:
        try:
            raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error: failed to parse YAML — {e}", file=sys.stderr)
            sys.exit(1)

    if raw is None or not isinstance(raw, dict):
        print("Error: preset file is empty or not a valid YAML mapping.", file=sys.stderr)
        sys.exit(1)

    try:
        preset_file = PresetFile.model_validate(raw)
    except ValidationError as e:
        print("Error: preset validation failed:", file=sys.stderr)
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            print(f"  {loc}: {err['msg']}", file=sys.stderr)
        sys.exit(1)

    return preset_file.meeting_preset
