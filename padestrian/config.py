import os
from pathlib import Path

from dotenv import load_dotenv

from padestrian.paths import PROJECT_ROOT


def load_env(*, fresh: bool = False) -> None:
    """Load variables from .env. Use fresh=True to re-read after editing the file."""
    load_dotenv(PROJECT_ROOT / ".env", override=fresh)


def require_env(name: str, *, fresh: bool = False) -> str:
    load_env(fresh=fresh)
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set. Add it to .env (see .env.example).")
    return value
