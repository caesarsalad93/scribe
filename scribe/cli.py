"""Typer CLI app — all commands and orchestration."""

import asyncio
import json
import logging
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

from .ai.analyzer import batch_action_items, diff_course_content
from .ai.summarizer import summarize_transcript
from .config import DEFAULT_DEEPGRAM_MODEL, DEFAULT_LANGUAGE, DEFAULT_OUTPUT_DIR
from .models import Summary, Transcript
from .transcription.audio import is_audio_file, is_video_file, prepare_audio
from .transcription.deepgram_provider import DeepgramProvider
from .utils import (
    ensure_output_dir,
    format_course_diff_markdown,
    format_transcript_markdown,
    format_transcript_raw_text,
    format_transcript_text,
    format_weekly_todo_markdown,
)

app = typer.Typer(help="Scribe — CLI transcription & course processor")
console = Console()
logger = logging.getLogger("scribe")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def _prompt_speaker_names(transcript: Transcript) -> Transcript:
    """Interactively prompt the user to name each detected speaker."""
    if len(transcript.speakers) <= 1:
        return transcript

    console.print(
        f"\n[bold]Detected {len(transcript.speakers)} speakers.[/bold]"
    )

    # Show a sample utterance for each speaker
    speaker_samples: dict[int, str] = {}
    for utt in transcript.utterances:
        if utt.speaker not in speaker_samples:
            sample = utt.text[:120] + ("..." if len(utt.text) > 120 else "")
            speaker_samples[utt.speaker] = sample

    name_map: dict[int, str] = {}
    for idx in sorted(speaker_samples):
        console.print(f'\n  Speaker {idx} sample: "{speaker_samples[idx]}"')
        name = Prompt.ask(
            f"  Name for Speaker {idx}",
            default=f"Speaker {idx}",
        )
        name_map[idx] = name

    # Apply names
    new_speakers = [name_map.get(i, f"Speaker {i}") for i in sorted(name_map)]
    new_utterances = []
    for utt in transcript.utterances:
        utt_copy = utt.model_copy()
        utt_copy.speaker_name = name_map.get(utt.speaker, f"Speaker {utt.speaker}")
        new_utterances.append(utt_copy)

    return transcript.model_copy(
        update={"speakers": new_speakers, "utterances": new_utterances}
    )


def _assign_speaker_names(
    transcript: Transcript, names: list[str]
) -> Transcript:
    """Assign speaker names from a pre-supplied list."""
    name_map = {i: names[i] if i < len(names) else f"Speaker {i}" for i in range(len(transcript.speakers))}

    new_speakers = [name_map[i] for i in sorted(name_map)]
    new_utterances = []
    for utt in transcript.utterances:
        utt_copy = utt.model_copy()
        utt_copy.speaker_name = name_map.get(utt.speaker, f"Speaker {utt.speaker}")
        new_utterances.append(utt_copy)

    return transcript.model_copy(
        update={"speakers": new_speakers, "utterances": new_utterances}
    )


@app.command()
def transcribe(
    file: Path = typer.Argument(..., help="Audio or video file to transcribe"),
    output: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output", "-o", help="Output directory"),
    format: str = typer.Option("markdown", "--format", help="Output format: markdown, json, text"),
    raw_text: bool = typer.Option(
        False,
        "--no-times",
        "--raw-text",
        help="Hide timestamps and speaker names in transcript output (text/markdown)",
    ),
    no_summary: bool = typer.Option(False, "--no-summary", help="Skip AI summarization"),
    no_diarize: bool = typer.Option(False, "--no-diarize", help="Disable speaker detection"),
    speakers: str = typer.Option("", "--speakers", help="Comma-separated speaker names"),
    model: str = typer.Option(DEFAULT_DEEPGRAM_MODEL, "--model", help="Deepgram model"),
    language: str = typer.Option(DEFAULT_LANGUAGE, "--language", help="Language code"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Transcribe audio/video with optional summarization."""
    _setup_logging(verbose)

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    if not (is_audio_file(file) or is_video_file(file)):
        console.print(f"[red]Unsupported file type: {file.suffix}[/red]")
        raise typer.Exit(1)

    if raw_text and format == "json":
        console.print(
            "[red]--no-times/--raw-text is not supported with --format json.[/red] "
            f"Current format: {format}"
        )
        raise typer.Exit(1)

    ensure_output_dir(output)

    async def _run() -> None:
        # Prepare audio
        audio_path, is_temp = prepare_audio(file)
        try:
            console.print(f"[bold]Transcribing:[/bold] {file.name}")
            if is_temp:
                console.print("  (extracted audio from video)")

            provider = DeepgramProvider()
            transcript = await provider.transcribe(
                str(audio_path),
                diarize=not no_diarize,
                model=model,
                language=language,
            )
            # Override source_file to show original
            transcript = transcript.model_copy(
                update={"source_file": str(file)}
            )

            console.print(
                f"  [green]Done.[/green] Duration: {transcript.duration:.1f}s, "
                f"Speakers: {len(transcript.speakers)}"
            )

            # Speaker names
            if speakers:
                name_list = [n.strip() for n in speakers.split(",")]
                transcript = _assign_speaker_names(transcript, name_list)
            elif not no_diarize and len(transcript.speakers) > 1:
                transcript = _prompt_speaker_names(transcript)

            # Summarization
            summary: Summary | None = None
            if not no_summary:
                console.print("  Generating summary...")
                text_for_summary = (
                    format_transcript_text(transcript)
                    if transcript.utterances
                    else transcript.raw_text
                )
                try:
                    summary = await summarize_transcript(text_for_summary)
                    console.print("  [green]Summary generated.[/green]")
                except Exception as e:
                    console.print(f"  [yellow]Summary failed: {e}[/yellow]")

            # Write output
            stem = file.stem
            if format == "json":
                out_file = output / f"{stem}.json"
                data = transcript.model_dump()
                if summary:
                    data["summary"] = summary.model_dump()
                out_file.write_text(json.dumps(data, indent=2))
            elif format == "text":
                out_file = output / f"{stem}.txt"
                text_output = (
                    format_transcript_raw_text(transcript)
                    if raw_text
                    else format_transcript_text(transcript)
                )
                out_file.write_text(text_output)
            else:
                out_file = output / f"{stem}.md"
                out_file.write_text(
                    format_transcript_markdown(
                        transcript, summary, raw_text=raw_text
                    )
                )

            console.print(f"\n[bold green]Output:[/bold green] {out_file}")

        finally:
            if is_temp:
                shutil.rmtree(Path(audio_path).parent, ignore_errors=True)

    asyncio.run(_run())


@app.command()
def course(
    video: Path = typer.Argument(..., help="Video file to transcribe"),
    text: Path = typer.Argument(..., help="Text file with course content"),
    output: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output", "-o", help="Output directory"),
    week: str = typer.Option("", "--week", help="Week label for batching"),
    model: str = typer.Option(DEFAULT_DEEPGRAM_MODEL, "--model", help="Deepgram model"),
    language: str = typer.Option(DEFAULT_LANGUAGE, "--language", help="Language code"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Diff video transcript against text, extract action items."""
    _setup_logging(verbose)

    if not video.exists():
        console.print(f"[red]Video file not found: {video}[/red]")
        raise typer.Exit(1)
    if not text.exists():
        console.print(f"[red]Text file not found: {text}[/red]")
        raise typer.Exit(1)

    ensure_output_dir(output)

    async def _run() -> None:
        # Transcribe video
        audio_path, is_temp = prepare_audio(video)
        try:
            console.print(f"[bold]Transcribing:[/bold] {video.name}")
            provider = DeepgramProvider()
            transcript = await provider.transcribe(
                str(audio_path), model=model, language=language
            )
            console.print("  [green]Transcription complete.[/green]")
        finally:
            if is_temp:
                shutil.rmtree(Path(audio_path).parent, ignore_errors=True)

        # Read course text
        course_text = text.read_text()

        # Get transcript text
        transcript_text = (
            format_transcript_text(transcript)
            if transcript.utterances
            else transcript.raw_text
        )

        # Diff
        console.print("  Analyzing differences...")
        diff = await diff_course_content(transcript_text, course_text)
        console.print(
            f"  [green]Found {len(diff.additions)} additions, "
            f"{len(diff.omissions)} omissions, "
            f"{len(diff.action_items)} action items.[/green]"
        )

        # Write markdown
        stem = video.stem
        md_file = output / f"{stem}_diff.md"
        md_file.write_text(format_course_diff_markdown(diff, week))
        console.print(f"  [bold green]Diff:[/bold green] {md_file}")

        # Write JSON sidecar for batch command
        json_file = output / f"{stem}_actions.json"
        actions_data = [
            {**a.model_dump(), "source": video.name}
            for a in diff.action_items
        ]
        json_file.write_text(json.dumps(actions_data, indent=2))
        console.print(f"  [bold green]Actions:[/bold green] {json_file}")

    asyncio.run(_run())


@app.command()
def batch(
    directory: Path = typer.Argument(..., help="Directory containing course action JSON files"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file path"),
    week: str = typer.Option("", "--week", help="Week label"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Consolidate multiple course outputs into a weekly to-do list."""
    _setup_logging(verbose)

    if not directory.exists():
        console.print(f"[red]Directory not found: {directory}[/red]")
        raise typer.Exit(1)

    # Find all *_actions.json files
    json_files = sorted(directory.glob("*_actions.json"))
    if not json_files:
        console.print("[yellow]No action JSON files found in directory.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[bold]Found {len(json_files)} action file(s).[/bold]")

    # Collect all action items
    all_items: list[dict] = []
    for jf in json_files:
        try:
            items = json.loads(jf.read_text())
            all_items.extend(items)
            console.print(f"  {jf.name}: {len(items)} items")
        except (json.JSONDecodeError, OSError) as e:
            console.print(f"  [yellow]Skipping {jf.name}: {e}[/yellow]")

    if not all_items:
        console.print("[yellow]No action items found.[/yellow]")
        raise typer.Exit(0)

    async def _run() -> None:
        console.print("  Consolidating action items...")
        consolidated = await batch_action_items(all_items, week)
        console.print(f"  [green]{len(consolidated)} consolidated items.[/green]")

        # Write output
        if output:
            out_file = output
        else:
            out_dir = ensure_output_dir(DEFAULT_OUTPUT_DIR)
            label = f"_week{week}" if week else ""
            out_file = out_dir / f"weekly_todo{label}.md"

        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(format_weekly_todo_markdown(consolidated, week))
        console.print(f"\n[bold green]Output:[/bold green] {out_file}")

    asyncio.run(_run())


if __name__ == "__main__":
    app()
