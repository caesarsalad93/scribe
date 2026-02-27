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


def download_url_video(
    url: str,
    output_dir: Path,
    progress_callback: Callable[[str], None] | None = None,
) -> Path:
    """Download best available video+audio for a URL into output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = output_dir / "%(title).120s.%(ext)s"

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
                f"Downloading video... {percent or ''}".strip(),
                f"{_fmt_size(downloaded)}/{_fmt_size(total)}",
            ]
            if speed:
                parts.append(f"at {speed}")
            if eta is not None:
                parts.append(f"ETA {eta}s")
            _notify(" | ".join(parts))
        elif status == "finished":
            _notify("Download complete. Finalizing video file...")

    opts: dict = {
        "format": "bestvideo*+bestaudio/best",
        "outtmpl": str(output_template),
        "noplaylist": True,
        "merge_output_format": "mp4",
        "nooverwrites": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_progress_hook],
    }

    media_suffixes = {
        ".mp4",
        ".mkv",
        ".webm",
        ".mov",
        ".avi",
        ".m4v",
    }

    def _collect_paths(info_obj: dict | None) -> list[Path]:
        if not info_obj:
            return []

        candidates: list[Path] = []
        for key in ("filepath", "_filename"):
            value = info_obj.get(key)
            if value:
                candidates.append(Path(str(value)))

        requested = info_obj.get("requested_downloads")
        if isinstance(requested, list):
            for item in requested:
                if isinstance(item, dict):
                    value = item.get("filepath")
                    if value:
                        candidates.append(Path(str(value)))

        entries = info_obj.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    candidates.extend(_collect_paths(entry))

        return candidates

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise RuntimeError("yt-dlp returned no media metadata.")
            if isinstance(info, dict) and info.get("entries"):
                entries = [entry for entry in info["entries"] if entry]
                if not entries:
                    raise RuntimeError("yt-dlp returned empty media entries.")
                info = entries[0]

            expected_path = Path(ydl.prepare_filename(info))
            result_info = ydl.extract_info(url, download=True)
    except Exception as e:
        raise RuntimeError(f"yt-dlp failed: {e}") from e

    info_paths = sorted(
        (
            p.resolve()
            for p in _collect_paths(result_info if isinstance(result_info, dict) else None)
            if p.exists() and p.is_file() and p.suffix.lower() in media_suffixes
        ),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    if info_paths:
        return info_paths[0]

    stem_matches = sorted(
        (
            p.resolve()
            for p in output_dir.glob(f"{expected_path.stem}.*")
            if p.is_file() and p.suffix.lower() in media_suffixes
        ),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    if stem_matches:
        return stem_matches[0]

    recent_media = sorted(
        (
            p.resolve()
            for p in output_dir.iterdir()
            if p.is_file() and p.suffix.lower() in media_suffixes
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if recent_media:
        return recent_media[0]

    raise RuntimeError("yt-dlp completed but no video file was produced.")
