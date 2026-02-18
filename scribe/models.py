"""Pydantic models for Scribe."""

from pydantic import BaseModel


class Utterance(BaseModel):
    speaker: int
    speaker_name: str = ""
    start: float
    end: float
    text: str


class Transcript(BaseModel):
    source_file: str
    duration: float = 0.0
    speakers: list[str] = []
    utterances: list[Utterance] = []
    raw_text: str = ""


class Summary(BaseModel):
    title: str = ""
    summary: str = ""
    key_points: list[str] = []
    action_items: list[str] = []


class ActionItem(BaseModel):
    description: str
    source: str = ""
    priority: str = "normal"


class CourseDiff(BaseModel):
    additions: list[str] = []
    omissions: list[str] = []
    combined_text: str = ""
    action_items: list[ActionItem] = []
