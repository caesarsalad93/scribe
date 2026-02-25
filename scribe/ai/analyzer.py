"""Course content diffing, action item extraction, and batching."""

import json

import anthropic

from ..config import DEFAULT_CLAUDE_MODEL, get_anthropic_api_key
from ..models import ActionItem, CourseDiff

DIFF_SYSTEM = """\
You are a course assistant. You receive a video transcript and written course text.
Internally reconcile both sources so nothing is missed, then produce a single
flat list of concrete action items a student should complete after the lesson.

Each action item must be specific and actionable (start with a verb).
Order items logically — setup tasks first, then core tasks, then optional/polish.

Respond with ONLY valid JSON matching this schema:
{
  "action_items": [
    {"description": "what to do", "priority": "high|normal|low"}
  ]
}"""

BATCH_SYSTEM = """\
You are consolidating action items from multiple course sessions into a single weekly to-do list.
Deduplicate similar items and organize by priority.

Respond with ONLY valid JSON — a list of objects:
[
  {"description": "what to do", "source": "which session", "priority": "high|normal|low"}
]"""


async def diff_course_content(transcript_text: str, course_text: str) -> CourseDiff:
    """Diff video transcript against course text using Claude."""
    client = anthropic.Anthropic(api_key=get_anthropic_api_key())

    user_msg = (
        "VIDEO TRANSCRIPT:\n---\n"
        + transcript_text
        + "\n---\n\nWRITTEN TEXT:\n---\n"
        + course_text
        + "\n---"
    )

    message = client.messages.create(
        model=DEFAULT_CLAUDE_MODEL,
        max_tokens=2048,
        system=DIFF_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    response_text = message.content[0].text  # type: ignore[union-attr]
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])

    data = json.loads(cleaned)

    action_items = [
        ActionItem(description=a["description"], priority=a.get("priority", "normal"))
        for a in data.get("action_items", [])
    ]

    return CourseDiff(
        action_items=action_items,
    )


async def batch_action_items(
    all_items: list[dict], week: str = ""
) -> list[ActionItem]:
    """Consolidate and deduplicate action items from multiple sessions."""
    if not all_items:
        return []

    client = anthropic.Anthropic(api_key=get_anthropic_api_key())

    user_msg = "ACTION ITEMS:\n" + json.dumps(all_items, indent=2)

    message = client.messages.create(
        model=DEFAULT_CLAUDE_MODEL,
        max_tokens=2048,
        system=BATCH_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    response_text = message.content[0].text  # type: ignore[union-attr]
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])

    data = json.loads(cleaned)
    return [ActionItem(**item) for item in data]
