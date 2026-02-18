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
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
