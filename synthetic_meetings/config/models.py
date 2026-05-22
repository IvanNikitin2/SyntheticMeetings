from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, field_validator


class Participant(BaseModel):
    role: str
    name: str
    personality: str
    voice: str
    verbosity: Optional[str] = None
    speaking_rate: Optional[str] = None
    pitch: Optional[str] = None
    style: Optional[str] = None
    emotion: Optional[str] = None


class ConversationStyle(BaseModel):
    tone: str
    pacing: str
    filler_words: str = "low"
    realism_level: str = "medium"
    overlapping_speech: str = "low"


class ActionItems(BaseModel):
    complexity: str
    count: int


class MeetingPreset(BaseModel):
    name: str
    vertical: str
    topic: str
    duration_minutes: int
    agenda_items: list[str] = []
    formality: str = "professional"
    interruption_frequency: str = "low"
    participants: list[Participant]
    conversation_style: ConversationStyle
    action_items: ActionItems
    system_prompt_override: Optional[str] = None

    @field_validator("participants")
    @classmethod
    def at_least_two_participants(cls, v: list[Participant]) -> list[Participant]:
        if len(v) < 2:
            raise ValueError("A meeting must have at least 2 participants.")
        if len(v) > 4:
            raise ValueError("A meeting supports at most 4 participants.")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def valid_duration(cls, v: int) -> int:
        if not (5 <= v <= 60):
            raise ValueError("duration_minutes must be between 5 and 60.")
        return v


class PresetFile(BaseModel):
    meeting_preset: MeetingPreset
