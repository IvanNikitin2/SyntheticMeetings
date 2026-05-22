from __future__ import annotations
from dataclasses import dataclass
from synthetic_meetings.config.models import MeetingPreset

_BASE_WPM = 130
_RATE_WPM = {"slow": 100, "medium": 130, "fast": 160}


def _effective_wpm(preset: MeetingPreset) -> float:
    rates = [_RATE_WPM.get(p.speaking_rate or "medium", _BASE_WPM) for p in preset.participants]
    return sum(rates) / len(rates)


def _speaker_list(preset: MeetingPreset) -> str:
    lines = []
    for p in preset.participants:
        desc = f"  {p.name} ({p.role}) — {p.personality}"
        if p.verbosity:
            desc += f", verbosity: {p.verbosity}"
        lines.append(desc)
    return "\n".join(lines)


_SYSTEM_PROMPT = """\
You write meeting transcripts as plain spoken dialogue. \
Format every line as exactly "Name: spoken text" — nothing else.

RULES:
- Output ONLY "Name: text" lines. No stage directions, no section headers, no markdown, no XML.
- Every speaker turn must be 3–5 full sentences. \
Never write fewer than 2 sentences unless it is a genuine one-word interruption like "Right." or "Agreed."
- Speakers must ask follow-up questions, disagree, share specific examples, reference earlier points, \
and elaborate at length before yielding the floor.
- Do NOT summarize or wrap up a topic early. Exhaust each subject fully before moving on.
- Think of this as a verbatim transcript of a real recorded meeting — people talk a lot.
- Use the exact speaker names provided. Do not introduce new speakers.
- Filler words: {filler_words}.
- Realism: {realism_level}.
- Interruptions: {interruption_frequency}.
"""


@dataclass
class SectionPrompt:
    label: str
    prompt: str
    min_turns: int


def build_system_prompt(preset: MeetingPreset) -> str:
    cs = preset.conversation_style
    return _SYSTEM_PROMPT.format(
        filler_words=cs.filler_words,
        realism_level=cs.realism_level,
        interruption_frequency=preset.interruption_frequency,
    )


def build_section_prompts(preset: MeetingPreset) -> list[SectionPrompt]:
    cs = preset.conversation_style
    ai = preset.action_items
    wpm = _effective_wpm(preset)
    total_minutes = preset.duration_minutes

    speakers = _speaker_list(preset)
    names = ", ".join(p.name for p in preset.participants)

    num_agenda = max(len(preset.agenda_items), 1)
    opening_minutes = total_minutes * 0.12
    closing_minutes = total_minutes * 0.18
    body_minutes = total_minutes - opening_minutes - closing_minutes
    per_agenda_minutes = body_minutes / num_agenda

    # Turns per minute calibrated so total output matches duration.
    # At 130 wpm, 4 sentences/turn ≈ 40 words/turn ≈ 18s/turn → ~3.3 turns/minute.
    # We use 3 to stay safely under target.
    turns_per_minute = 4.5

    def turns(minutes: float) -> int:
        return max(4, int(minutes * turns_per_minute))

    sections: list[SectionPrompt] = []

    opening_prompt = (
        f"Write the OPENING of a {total_minutes}-minute meeting.\n"
        f"Topic: {preset.topic} | Industry: {preset.vertical} | Formality: {preset.formality} | Tone: {cs.tone}\n\n"
        f"Speakers:\n{speakers}\n\n"
        f"Write at least {turns(opening_minutes)} speaker turns.\n"
        f"Each turn must be 3–5 sentences.\n"
        f"Include: greeting, quick check-in, each person gives a brief status update.\n"
        f"Do NOT start discussing the agenda yet. Do NOT wrap up.\n"
        f"Use names: {names}. Format: 'Name: text'."
    )
    sections.append(SectionPrompt("Opening", opening_prompt, turns(opening_minutes)))

    for i, item in enumerate(preset.agenda_items):
        is_last = i == len(preset.agenda_items) - 1
        extra = (
            f"Surface {ai.count} action items of {ai.complexity} complexity — assign each one explicitly. "
            if is_last else ""
        )
        item_prompt = (
            f"Continue the meeting transcript.\n"
            f"Now write the discussion of AGENDA ITEM: '{item}'.\n\n"
            f"Speakers:\n{speakers}\n\n"
            f"Write at least {turns(per_agenda_minutes)} speaker turns.\n"
            f"Each turn must be 3–5 sentences.\n"
            f"Include back-and-forth, at least one concern or question, specific examples.\n"
            f"{extra}"
            f"Do NOT wrap up the meeting. Do NOT move to another agenda item.\n"
            f"Format: 'Name: text'."
        )
        sections.append(SectionPrompt(f"Agenda: {item}", item_prompt, turns(per_agenda_minutes)))

    closing_prompt = (
        f"Continue the meeting transcript. All agenda items have been discussed.\n"
        f"Now write the CLOSING section.\n\n"
        f"Speakers:\n{speakers}\n\n"
        f"Write at least {turns(closing_minutes)} speaker turns.\n"
        f"Each turn must be 3–5 sentences.\n"
        f"Include: decisions recap, assignment of {ai.count} action items with owners and deadlines, farewell.\n"
        f"This is the final section. End the meeting naturally.\n"
        f"Format: 'Name: text'."
    )
    sections.append(SectionPrompt("Closing", closing_prompt, turns(closing_minutes)))

    return sections


def build_prompts(preset: MeetingPreset) -> tuple[str, str]:
    system_prompt = build_system_prompt(preset)
    sections = build_section_prompts(preset)
    combined_user_prompt = "\n\n---\n\n".join(s.prompt for s in sections)
    return system_prompt, combined_user_prompt
