"""Environment loading and defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def get_deepgram_api_key() -> str:
    key = os.environ.get("DEEPGRAM_API_KEY", "")
    if not key:
        raise RuntimeError(
            "DEEPGRAM_API_KEY not set. Add it to .env or export it."
        )
    return key


def get_deepgram_timeout_seconds() -> int:
    value = os.environ.get("DEEPGRAM_TIMEOUT_SECONDS", "600")
    try:
        timeout = int(value)
    except ValueError as e:
        raise RuntimeError(
            "DEEPGRAM_TIMEOUT_SECONDS must be an integer."
        ) from e
    if timeout <= 0:
        raise RuntimeError(
            "DEEPGRAM_TIMEOUT_SECONDS must be greater than 0."
        )
    return timeout


def get_deepgram_max_retries() -> int:
    value = os.environ.get("DEEPGRAM_MAX_RETRIES", "2")
    try:
        retries = int(value)
    except ValueError as e:
        raise RuntimeError(
            "DEEPGRAM_MAX_RETRIES must be an integer."
        ) from e
    if retries < 0:
        raise RuntimeError(
            "DEEPGRAM_MAX_RETRIES cannot be negative."
        )
    return retries


def get_anthropic_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Add it to .env or export it."
        )
    return key


DEFAULT_OUTPUT_DIR = Path("./output")
DEFAULT_DEEPGRAM_MODEL = "nova-2"
DEFAULT_LANGUAGE = "en"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
