from __future__ import annotations

from extraction.parsers import (
    extract_campaign_record, extract_competitor_record, extract_hotel_records,
    extract_partner_updates, extract_trend_signals,
)
from logger import get_logger
from mcp.schemas import ToolResult

log = get_logger("mcp.extract_tools")

_EXTRACTORS = {
    "hotel_pricing_watch": lambda html, url, key: [r.model_dump() for r in extract_hotel_records(html, url, key)],
    "campaign_page_monitoring": lambda html, url, key: (
        lambda rec: [rec.model_dump()] if rec else []
    )(extract_campaign_record(html, url, key)),
    "competitor_offer_tracking": lambda html, url, key: (
        lambda rec: [rec.model_dump()] if rec else []
    )(extract_competitor_record(html, url, key)),
    "partner_update_review": lambda html, url, key: [r.model_dump() for r in extract_partner_updates(html, url, key)],
    "travel_trend_scanning": lambda html, url, key: [r.model_dump() for r in extract_trend_signals(html, url, key)],
}


def extract(workflow_type: str, html_excerpt: str, source_url: str, entity_key: str) -> ToolResult:
    # deterministic-first extraction (extraction/parsers.py) - never sends
    # full HTML to an LLM; this tool IS the deterministic layer, semantic/LLM
    # fallback would be a separate tool called only when this returns empty
    extractor = _EXTRACTORS.get(workflow_type)
    if extractor is None:
        return ToolResult(success=False, error_type="UNKNOWN", message=f"No extractor for workflow '{workflow_type}'")

    records = extractor(html_excerpt, source_url, entity_key)
    if not records:
        log.warning(f"extract: workflow={workflow_type} entity={entity_key} produced no records")
        return ToolResult(success=False, error_type="EXTRACTION_FAILED", message="Extraction produced no records")

    low_confidence = sum(1 for r in records if r.get("confidence", 1.0) < 0.7)
    log.info(f"extract: workflow={workflow_type} entity={entity_key} -> {len(records)} record(s), {low_confidence} low-confidence")
    return ToolResult(success=True, data={"records": records, "low_confidence_count": low_confidence})
