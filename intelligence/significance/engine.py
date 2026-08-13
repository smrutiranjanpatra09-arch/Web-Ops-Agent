from __future__ import annotations

from extraction.normalizers import normalize_label

# configurable significance thresholds (MASTER_SPEC section 11) - deterministic,
# never LLM-computed. Percent buckets are on abs(delta_pct).
THRESHOLDS = {
    "insignificant": 1.0,
    "minor": 5.0,
    "notable": 15.0,
    # anything above "notable" is "significant"
}

NOISE_FIELDS = {"extracted_at", "source_url", "evidence_snippet"}


def classify_significance(delta_pct: float | None) -> str:
    if delta_pct is None:
        return "insignificant"
    magnitude = abs(delta_pct)
    if magnitude < THRESHOLDS["insignificant"]:
        return "insignificant"
    if magnitude < THRESHOLDS["minor"]:
        return "minor"
    if magnitude < THRESHOLDS["notable"]:
        return "notable"
    return "significant"


def is_noise(field_name: str, previous_value: str | None, current_value: str | None) -> tuple[bool, str | None]:
    # distinguishes real business change from formatting/tracking-param/
    # timestamp-only noise (MASTER_SPEC section 11) - never emit a signal from this
    if field_name in NOISE_FIELDS:
        return True, f"field '{field_name}' is metadata, not a business value"
    if previous_value is not None and current_value is not None:
        if normalize_label(previous_value).casefold() == normalize_label(current_value).casefold():
            return True, "value unchanged after case/whitespace normalization"
    return False, None
