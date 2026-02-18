"""Claude summarization of transcripts."""

import json

import anthropic

from ..config import DEFAULT_CLAUDE_MODEL, get_anthropic_api_key
from ..models import Summary

SUMMARIZE_PROMPT = """\
You are analyzing a transcript. Provide a structured summary in JSON format.

Respond with ONLY valid JSON matching this schema:
{
  "title": "A concise title for this transcript",
  "summary": "2-3 sentence summary of the content",
  "key_points": ["point 1", "point 2", ...],
  "action_items": ["action 1", "action 2", ...]
}

If there are no action items, use an empty list.

Transcript:
"""


async def summarize_transcript(text: str) -> Summary:
    """Summarize transcript text using Claude."""
    client = anthropic.Anthropic(api_key=get_anthropic_api_key())

    message = client.messages.create(
        model=DEFAULT_CLAUDE_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": SUMMARIZE_PROMPT + text}
        ],
    )

    response_text = message.content[0].text  # type: ignore[union-attr]

    # Parse JSON from response (handle markdown code blocks)
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` wrapper
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])

    data = json.loads(cleaned)
    return Summary(**data)
