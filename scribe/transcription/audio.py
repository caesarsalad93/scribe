"""Audio extraction from video files via ffmpeg."""

import shutil
import subprocess
import tempfile
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma"}


def is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def _has_audio_stream(file_path: Path) -> bool:
    """Check if a file contains an audio stream using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-i", str(file_path), "-show_streams",
         "-select_streams", "a", "-loglevel", "quiet"],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def extract_audio(video_path: Path) -> Path:
    """Extract audio from a video file using ffmpeg. Returns path to temp .wav file."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg not found. Install it to process video files."
        )

    if not _has_audio_stream(video_path):
        raise RuntimeError(
            f"No audio stream found in {video_path.name}. "
            "This video has no audio to transcribe."
        )

    temp_dir = tempfile.mkdtemp(prefix="scribe_")
    output_path = Path(temp_dir) / f"{video_path.stem}.wav"

    result = subprocess.run(
        [
            "ffmpeg", "-i", str(video_path),
            "-vn",                  # no video
            "-acodec", "pcm_s16le", # WAV format
            "-ar", "16000",         # 16kHz sample rate (good for speech)
            "-ac", "1",             # mono
            "-y",                   # overwrite
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    return output_path


def prepare_audio(file_path: Path) -> tuple[Path, bool]:
    """Prepare audio for transcription. Returns (audio_path, is_temp).

    If the input is a video, extracts audio to a temp file.
    If it's already audio, returns the original path.
    """
    if is_video_file(file_path):
        return extract_audio(file_path), True
    return file_path, False
