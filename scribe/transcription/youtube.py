"""YouTube audio download helper using yt-dlp."""

import tempfile
from collections.abc import Callable
from pathlib import Path

import yt_dlp


def _fmt_size(value: int | None) -> str:
    if not value or value <= 0:
        return "?"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    return f"{size:.1f}{units[idx]}"


def download_youtube_audio(
    url: str,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[Path, Path]:
    """Download best-quality audio from a YouTube URL.

    Returns (audio_file_path, temp_dir_path).
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="scribe_yt_"))
    output_template = temp_dir / "%(title).120s.%(ext)s"

    def _notify(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    def _progress_hook(data: dict) -> None:
        status = data.get("status")
        if status == "downloading":
            percent = str(data.get("_percent_str", "")).strip()
            speed = str(data.get("_speed_str", "")).strip()
            eta = data.get("eta")
            downloaded = data.get("downloaded_bytes")
            total = data.get("total_bytes") or data.get("total_bytes_estimate")

            parts = [
                f"Downloading audio... {percent or ''}".strip(),
                f"{_fmt_size(downloaded)}/{_fmt_size(total)}",
            ]
            if speed:
                parts.append(f"at {speed}")
            if eta is not None:
                parts.append(f"ETA {eta}s")
            _notify(" | ".join(parts))
        elif status == "finished":
            _notify("Download complete. Converting to m4a...")

    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(output_template),
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise RuntimeError(f"yt-dlp failed: {e}") from e

    audio_files = sorted(
        p for p in temp_dir.iterdir() if p.is_file()
    )
    if not audio_files:
        raise RuntimeError("yt-dlp completed but no audio file was produced.")

    return audio_files[0], temp_dir
