# central logging setup - every module grabs its logger via get_logger(__name__)
# instead of print(), so run history ends up in logs/agent.log with real
# timestamps, levels, and module names instead of scattered stdout lines.
from __future__ import annotations

import logging
import os
from pathlib import Path

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "agent.log"

_configured = False


def _configure_root():
    global _configured
    if _configured:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger("webops")
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.propagate = False

    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"webops.{name}")


class RunContext:
    # wraps a logger so every message carries the correlation IDs needed to
    # reconstruct a full workflow from logs alone (engineering guidelines, section 21):
    # task_id, run_id, step_id, trace_id, evidence_id. Only run_id and module
    # are required; the rest are optional and get added as they become known
    # during a run (e.g. evidence_id only exists after a browse succeeds).
    def __init__(self, run_id: str, module: str, *, task_id: str | None = None,
                 trace_id: str | None = None, step_id: str | None = None,
                 evidence_id: str | None = None):
        self._logger = get_logger(module)
        self._run_id = run_id
        self._task_id = task_id
        self._trace_id = trace_id or run_id
        self._step_id = step_id
        self._evidence_id = evidence_id

    def with_context(self, **kwargs) -> "RunContext":
        # returns a new RunContext with additional/updated correlation IDs,
        # e.g. log.with_context(evidence_id=ev.id) once evidence exists
        merged = {
            "task_id": self._task_id, "trace_id": self._trace_id,
            "step_id": self._step_id, "evidence_id": self._evidence_id,
        }
        merged.update(kwargs)
        return RunContext(self._run_id, self._logger.name.removeprefix("webops."), **merged)

    def _fmt(self, msg: str) -> str:
        parts = [f"run={self._run_id}"]
        if self._task_id:
            parts.append(f"task={self._task_id}")
        if self._step_id:
            parts.append(f"step={self._step_id}")
        if self._evidence_id:
            parts.append(f"evidence={self._evidence_id}")
        if self._trace_id and self._trace_id != self._run_id:
            parts.append(f"trace={self._trace_id}")
        return f"[{' '.join(parts)}] {msg}"

    def info(self, msg: str):
        self._logger.info(self._fmt(msg))

    def warning(self, msg: str):
        self._logger.warning(self._fmt(msg))

    def error(self, msg: str):
        self._logger.error(self._fmt(msg))

    def debug(self, msg: str):
        self._logger.debug(self._fmt(msg))
