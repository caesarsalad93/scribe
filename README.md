# Scribe

CLI tool for transcription and course-processing workflows.

## Requirements

- Python `3.12+`
- `ffmpeg` and `ffprobe` on PATH (needed for video inputs)
- `yt-dlp` on PATH (needed for `transcribe-url` and `download-url`)
- Deepgram API key
- Anthropic API key (needed for summary/course/batch AI steps)

## Setup

```bash
# from repo root
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Edit `.env`:

```env
DEEPGRAM_API_KEY=your_key_here
DEEPGRAM_TIMEOUT_SECONDS=600
DEEPGRAM_MAX_RETRIES=2
ANTHROPIC_API_KEY=your_key_here
```

## Main Commands

Run help:

```bash
scribe --help
```

Command patterns:

```bash
scribe <command> [args]
scribe <command> --help
```

Examples:

```bash
scribe transcribe --help
scribe transcribe-url --help
scribe download-url --help
scribe course --help
scribe batch --help
```

Transcribe audio/video (writes to `./output` by default):

```bash
scribe transcribe path/to/file.mp4
```

Transcribe directly from YouTube URL:

```bash
scribe transcribe-url "https://www.youtube.com/watch?v=VIDEO_ID"
```

Download video from a URL without transcription (works with yt-dlp supported URLs):

```bash
scribe download-url "https://www.youtube.com/watch?v=VIDEO_ID"
```

Note: this will not work: `scribe https://www.youtube.com/watch?v=VIDEO_ID`

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
scribe transcribe-url "https://www.youtube.com/watch?v=VIDEO_ID" --format text --no-times
scribe download-url "https://www.youtube.com/watch?v=VIDEO_ID" --output output/videos
```

Note: `--no-times` works with `--format text` and `--format markdown` (not `json`).

## Runtime Notes

- `transcribe-url` now shows live download progress (percent, size, speed, ETA) and fallback log lines in terminals that do not render dynamic status updates.
- `download-url` saves best available video+audio to your output directory, skipping if the same output title already exists.
- Deepgram requests use configurable timeout/retry settings from `.env`:
  - `DEEPGRAM_TIMEOUT_SECONDS` (default `600`)
  - `DEEPGRAM_MAX_RETRIES` (default `2`)
- Summarization is more detailed and includes JSON-parse recovery + one automatic retry if the model returns invalid JSON.

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
- `scribe transcribe-url ...`:
  - `output/<downloaded-title>.md` (default format)
  - `output/<downloaded-title>.json` (`--format json`)
  - `output/<downloaded-title>.txt` (`--format text`)
- `scribe download-url ...`:
  - `output/<downloaded-title>.<ext>` (video file, extension depends on source/merge output)
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

## Troubleshooting

- `zsh: command not found: scribe`
  - Install CLI into your active venv:
    ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install -e .
    which scribe
    ```
  - In new terminal tabs, re-activate the venv:
    ```bash
    source .venv/bin/activate
    ```
- URL command fails
  - Use the correct command:
    ```bash
    scribe transcribe-url "https://www.youtube.com/watch?v=VIDEO_ID"
    scribe download-url "https://www.youtube.com/watch?v=VIDEO_ID"
    ```
  - Verify tools are installed:
    ```bash
    yt-dlp --version
    ffmpeg -version
    ```
