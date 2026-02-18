"""Timestamps, file helpers, markdown formatting."""

from pathlib import Path

from .models import ActionItem, CourseDiff, Summary, Transcript


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_transcript_markdown(
    transcript: Transcript, summary: Summary | None = None
) -> str:
    """Format a transcript (and optional summary) as markdown."""
    lines: list[str] = []
    source_name = Path(transcript.source_file).stem
    lines.append(f"# Transcript: {source_name}\n")

    if transcript.duration > 0:
        lines.append(f"**Duration:** {format_timestamp(transcript.duration)}\n")

    if transcript.speakers:
        lines.append(
            f"**Speakers:** {', '.join(transcript.speakers)}\n"
        )

    # Summary section
    if summary:
        if summary.title:
            lines.append(f"## {summary.title}\n")
        if summary.summary:
            lines.append(f"{summary.summary}\n")
        if summary.key_points:
            lines.append("### Key Points\n")
            for point in summary.key_points:
                lines.append(f"- {point}")
            lines.append("")
        if summary.action_items:
            lines.append("### Action Items\n")
            for item in summary.action_items:
                lines.append(f"- [ ] {item}")
            lines.append("")

    # Transcript section
    lines.append("---\n")
    lines.append("## Transcript\n")

    if transcript.utterances:
        for utt in transcript.utterances:
            ts = format_timestamp(utt.start)
            name = utt.speaker_name or f"Speaker {utt.speaker}"
            lines.append(f"**[{ts}] {name}:** {utt.text}\n")
    else:
        lines.append(transcript.raw_text)

    return "\n".join(lines)


def format_transcript_text(transcript: Transcript) -> str:
    """Format transcript as plain text."""
    lines: list[str] = []
    if transcript.utterances:
        for utt in transcript.utterances:
            ts = format_timestamp(utt.start)
            name = utt.speaker_name or f"Speaker {utt.speaker}"
            lines.append(f"[{ts}] {name}: {utt.text}")
    else:
        lines.append(transcript.raw_text)
    return "\n".join(lines)


def format_course_diff_markdown(diff: CourseDiff, week: str = "") -> str:
    """Format a course diff as markdown."""
    lines: list[str] = []
    title = f"# Course Diff — Week {week}" if week else "# Course Diff"
    lines.append(f"{title}\n")

    if diff.additions:
        lines.append("## In Video Only (Additions)\n")
        for item in diff.additions:
            lines.append(f"- {item}")
        lines.append("")

    if diff.omissions:
        lines.append("## In Text Only (Omissions)\n")
        for item in diff.omissions:
            lines.append(f"- {item}")
        lines.append("")

    if diff.action_items:
        lines.append("## Action Items\n")
        for item in diff.action_items:
            priority_tag = f" [{item.priority}]" if item.priority != "normal" else ""
            lines.append(f"- [ ] {item.description}{priority_tag}")
        lines.append("")

    return "\n".join(lines)


def format_weekly_todo_markdown(
    action_items: list[ActionItem], week: str = ""
) -> str:
    """Format consolidated action items as a weekly to-do list."""
    lines: list[str] = []
    title = f"# Weekly To-Do — Week {week}" if week else "# Weekly To-Do"
    lines.append(f"{title}\n")

    # Group by priority
    high = [a for a in action_items if a.priority == "high"]
    normal = [a for a in action_items if a.priority == "normal"]
    low = [a for a in action_items if a.priority == "low"]

    if high:
        lines.append("## High Priority\n")
        for item in high:
            src = f" *(from {item.source})*" if item.source else ""
            lines.append(f"- [ ] {item.description}{src}")
        lines.append("")

    if normal:
        lines.append("## Tasks\n")
        for item in normal:
            src = f" *(from {item.source})*" if item.source else ""
            lines.append(f"- [ ] {item.description}{src}")
        lines.append("")

    if low:
        lines.append("## Low Priority\n")
        for item in low:
            src = f" *(from {item.source})*" if item.source else ""
            lines.append(f"- [ ] {item.description}{src}")
        lines.append("")

    return "\n".join(lines)
