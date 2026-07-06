# Synthetic Meetings

Converts SSML files to meeting audio. Azure Neural TTS synthesizes each speaker turn individually, then PyDub merges all turns into a final audio file.

---

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) — required by PyDub for MP3 export
- An Azure Speech resource (key + region)

---

## Setup

```bash
git clone <repo-url>
cd SyntheticMeetings

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and fill in your Azure keys
```

---

## Configuration

### `.env`

```ini
AZURE_TTS_KEY=your-azure-key
AZURE_TTS_REGION=eastus
```

---

## Usage

Place one or more `.ssml` files in the `input/` folder, then run:

```bash
# Process all .ssml files in input/
python3 main.py

# Process a specific file
python3 main.py input/my_meeting.ssml

# Process multiple specific files
python3 main.py input/meeting_a.ssml input/meeting_b.ssml
```

---

## Output

Each SSML file produces a folder at `output/YYYY-MM-DD_<filename>/`:

```
output/2026-05-22_my_meeting/
├── meeting.ssml          # Copy of the input SSML
├── transcript.txt        # [Speaker]: text — one line per turn
├── speakers/
│   ├── turn_001_Alex.wav
│   ├── turn_002_Sara.wav
│   └── ...
├── merged_meeting.wav    # All turns concatenated
└── merged_meeting.mp3    # Same, MP3 encoded
```

---

## SSML Format

Each speaker turn must be a `<voice>` element inside the root `<speak>` element:

```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <voice name="en-US-AvaNeural">
    Hello, let's get started with today's standup.
  </voice>
  <voice name="en-US-AndrewNeural">
    Sure. Yesterday I finished the API integration.
  </voice>
</speak>
```

# Azure HD Voices (East US)

If your Speech resource is in **East US (`eastus`)**, you can use Microsoft's newer **Dragon HD** voices, which sound significantly more natural than the classic `*Neural` voices.

## Dragon HD Voices

### Female
```text
en-US-Ava:DragonHDLatestNeural
en-US-Emma:DragonHDLatestNeural
```

### Male
```text
en-US-Andrew:DragonHDLatestNeural
en-US-Andrew2:DragonHDLatestNeural
en-US-Brian:DragonHDLatestNeural
en-US-Adam:DragonHDLatestNeural
en-US-Steffan:DragonHDLatestNeural
en-US-Davis:DragonHDLatestNeural
```

---

## Dragon HD Omni (Newest Generation)

If your Speech SDK/API version supports them, you can also try:

```text
en-US-Ava:DragonHDOmniLatestNeural
en-US-Andrew:DragonHDOmniLatestNeural
```

These use Microsoft's newest speech model with improved prosody and more natural conversational speech.

---

## Classic Neural Voices (Fallback)

If your application only supports the classic voice names, these remain excellent choices:

### Female
```text
en-US-AvaNeural
en-US-EmmaNeural
en-US-JennyNeural
```

### Male
```text
en-US-AndrewNeural
en-US-BrianNeural
en-US-GuyNeural
```

---

## Recommended Voices

### Best Female
1. `en-US-Ava:DragonHDLatestNeural`
2. `en-US-Emma:DragonHDLatestNeural`
3. `en-US-AvaNeural`

### Best Male
1. `en-US-Andrew:DragonHDLatestNeural`
2. `en-US-Brian:DragonHDLatestNeural`
3. `en-US-AndrewNeural`
## Troubleshooting

| Error | Fix |
|---|---|
| `AZURE_TTS_KEY is not set` | Add your Azure Speech key to `.env` |
| `failed to export MP3` | Install ffmpeg and ensure it is in your PATH |
| `SSML contains no <voice> elements` | Check your SSML — each turn must be a `<voice>` element |
| `invalid XML` | Your SSML file has malformed XML — validate it before running |
