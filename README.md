# Scribe

CLI tool for transcription and course-processing workflows.

## Requirements

- Python `3.12+`
- `ffmpeg` and `ffprobe` on PATH (needed for video inputs)
- Deepgram API key
- Anthropic API key (needed for summary/course/batch AI steps)

## Setup

```bash
# from repo root
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Edit `.env`:

```env
DEEPGRAM_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

## Main Commands

Run help:

```bash
scribe --help
```

Transcribe audio/video (writes to `./output` by default):

```bash
scribe transcribe path/to/file.mp4
```

Useful options:

```bash
scribe transcribe path/to/file.mp4 --output output --format markdown
scribe transcribe path/to/file.mp4 --output output --format markdown --no-times
scribe transcribe path/to/file.mp4 --format json
scribe transcribe path/to/file.mp4 --format text
scribe transcribe path/to/file.mp4 --format text --no-times
scribe transcribe path/to/file.mp4 --no-summary
scribe transcribe path/to/file.mp4 --no-diarize
scribe transcribe path/to/file.mp4 --speakers "Alex,Sam"
scribe transcribe path/to/file.mp4 --model nova-2 --language en -v
```

Note: `--no-times` works with `--format text` and `--format markdown` (not `json`).

Course mode (transcribe video, compare with text file, extract action items):

```bash
scribe course path/to/lesson.mp4 path/to/course-notes.txt
```

Useful options:

```bash
scribe course path/to/lesson.mp4 path/to/course-notes.txt --week 3 --output output -v
```

Batch mode (merge `*_actions.json` files into one weekly to-do):

```bash
scribe batch output --week 3
```

Useful options:

```bash
scribe batch output --output output/weekly_todo_week3.md -v
```

## Output Files

- `scribe transcribe ...`:
  - `output/<input-stem>.md` (default format)
  - `output/<input-stem>.md` transcript body without times/speakers (`--format markdown --no-times`)
  - `output/<input-stem>.json` (`--format json`)
  - `output/<input-stem>.txt` (`--format text`)
  - `output/<input-stem>.txt` lines without times/speakers (`--format text --no-times`)
- `scribe course ...`:
  - `output/<video-stem>_diff.md`
  - `output/<video-stem>_actions.json`
- `scribe batch ...`:
  - `output/weekly_todo.md` (or `output/weekly_todo_week<week>.md`)

## Fast Daily Workflow

```bash
source .venv/bin/activate
scribe transcribe recordings/meeting.mp4 --speakers "Alex,Jordan"
```
