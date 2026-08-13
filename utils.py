# shared helpers used across agents/extraction/backend - anything generic
# enough that it doesn't belong to one specific module lives here.
from __future__ import annotations

import functools
import os
import time
from typing import Callable, TypeVar

from logger import get_logger

_log = get_logger("utils")

T = TypeVar("T")

REQUIRED_ENV_VARS = ["MOCK_SITE_BASE_URL", "DATABASE_PATH", "SNAPSHOT_DIR"]


def check_required_env() -> list[str]:
    # returns the list of required env vars that are missing, so callers can
    # decide whether to warn or hard-fail at startup
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        _log.warning(f"Missing environment variables: {', '.join(missing)}")
    return missing


def retry(times: int = 2, delay_seconds: float = 1.0, exceptions: tuple = (Exception,)):
    # simple retry decorator for flaky I/O (browser worker, LLM calls, mock site
    # requests) - logs each failed attempt instead of failing silently
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if times < 1:
            raise ValueError("retry() requires times >= 1")

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    _log.warning(f"{func.__name__} attempt {attempt}/{times} failed: {exc}")
                    if attempt < times:
                        time.sleep(delay_seconds)
            raise last_exc

        return wrapper

    return decorator


def safe_float(value, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def truncate(text: str, max_len: int = 300) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
