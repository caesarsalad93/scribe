"""YouTube audio download helper using yt-dlp."""

import shutil
import subprocess
import tempfile
from pathlib import Path


def download_youtube_audio(url: str) -> tuple[Path, Path]:
    """Download best-quality audio from a YouTube URL.

    Returns (audio_file_path, temp_dir_path).
    """
    if not shutil.which("yt-dlp"):
        raise RuntimeError(
            "yt-dlp not found. Install it to use transcribe-url."
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="scribe_yt_"))
    output_template = temp_dir / "%(title).120s.%(ext)s"

    result = subprocess.run(
        [
            "yt-dlp",
            "--extract-audio",
            "--audio-format",
            "m4a",
            "--audio-quality",
            "0",
            "--no-playlist",
            "--output",
            str(output_template),
            url,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr or result.stdout}")

    audio_files = sorted(
        p for p in temp_dir.iterdir() if p.is_file()
    )
    if not audio_files:
        raise RuntimeError("yt-dlp completed but no audio file was produced.")

    return audio_files[0], temp_dir
