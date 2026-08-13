from __future__ import annotations

from pydantic import BaseModel


class ToolResult(BaseModel):
    # every MCP tool returns this shape (engineering guidelines, section 15/§9: structured
    # output, logged, policy-checked) - success carries data, failure carries
    # an error_type from the taxonomy plus a message
    success: bool
    data: dict | None = None
    error_type: str | None = None
    message: str | None = None
