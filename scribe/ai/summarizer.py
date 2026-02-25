"""Claude summarization of transcripts."""

import json
import re

import anthropic

from ..config import DEFAULT_CLAUDE_MODEL, get_anthropic_api_key
from ..models import Summary

SUMMARIZE_PROMPT = """\
You are analyzing a transcript. Provide a structured summary in JSON format.

Respond with ONLY valid JSON matching this schema:
{
  "title": "A concise title for this transcript",
  "summary": "A detailed summary of the content",
  "key_points": ["point 1", "point 2", ...],
  "action_items": ["action 1", "action 2", ...]
}

Quality requirements:
- Be thorough. Capture the full flow of the conversation, major arguments, decisions, and outcomes.
- Write a substantial summary (roughly 8-14 sentences).
- Include specific details (names, commitments, constraints, tradeoffs, timelines) when present.
- For key_points, include 8-15 concrete bullets, not generic statements.
- For action_items, include explicit owner and deadline when available from the transcript.
- If no action items are present, return an empty list.

Transcript:
"""


def _parse_summary_json(response_text: str) -> dict:
    """Parse summary JSON, tolerating common wrapper formats."""
    cleaned = response_text.strip()
    candidates: list[str] = [cleaned]

    # Handle fenced code blocks, e.g. ```json ... ```
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if len(lines) >= 3:
            candidates.append("\n".join(lines[1:-1]).strip())

    # Extract fenced JSON blocks.
    for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL):
        candidates.append(match.group(1).strip())

    # Extract the broadest object-like payload.
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidates.append(cleaned[first : last + 1].strip())

    errors: list[Exception] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            data = json.loads(candidate)
            if not isinstance(data, dict):
                raise ValueError("Summary payload must be a JSON object.")
            return data
        except Exception as e:
            errors.append(e)

    # Raise the last parse error with a compact hint.
    hint = cleaned[:300].replace("\n", "\\n")
    last_err = errors[-1] if errors else ValueError("No JSON candidate found.")
    raise ValueError(f"Could not parse summary JSON. Raw head: {hint}") from last_err


async def summarize_transcript(text: str) -> Summary:
    """Summarize transcript text using Claude."""
    client = anthropic.Anthropic(api_key=get_anthropic_api_key())

    last_error: Exception | None = None
    for attempt in range(2):
        suffix = ""
        if attempt > 0:
            suffix = (
                "\n\nIMPORTANT: Your previous response was invalid JSON. "
                "Return ONLY one valid JSON object and nothing else."
            )

        message = client.messages.create(
            model=DEFAULT_CLAUDE_MODEL,
            max_tokens=3200,
            messages=[
                {"role": "user", "content": SUMMARIZE_PROMPT + text + suffix}
            ],
        )

        response_text = message.content[0].text  # type: ignore[union-attr]
        try:
            data = _parse_summary_json(response_text)
            return Summary(**data)
        except Exception as e:
            last_error = e

    if last_error:
        raise last_error
    raise RuntimeError("Summary generation failed with unknown error.")
