from __future__ import annotations

from pydantic import BaseModel


class SourceResponse(BaseModel):
    id: str
    domain: str
    category: str
    owner: str
    health_state: str
    consecutive_failures: int
    total_runs: int
    total_failures: int
