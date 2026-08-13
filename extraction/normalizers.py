# normalization helpers applied to raw scraped strings before they become
# structured records: currency, dates, location/label text, and record dedup.
# kept separate from parsers.py so parsing (find the element) and normalizing
# (clean the value) stay independently testable.
from __future__ import annotations

import re
from datetime import datetime

CURRENCY_RE = re.compile(r"\b([A-Z]{3})\s*([\d,]+(?:\.\d+)?)")
BARE_AMOUNT_RE = re.compile(r"([\d,]+(?:\.\d+)?)")
PERCENT_RE = re.compile(r"([\d.]+)\s*%")

CURRENCY_SYMBOLS = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP"}

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
]


def normalize_currency(raw: str) -> tuple[str | None, float | None]:
    # handles "INR 6,500", "₹6500", "6,500" (no currency), "INR 6500.50"
    if not raw:
        return None, None
    text = raw.strip()

    match = CURRENCY_RE.search(text)
    if match:
        return match.group(1), _to_float(match.group(2))

    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text:
            amount = BARE_AMOUNT_RE.search(text)
            return code, _to_float(amount.group(1)) if amount else None

    amount = BARE_AMOUNT_RE.search(text)
    if amount:
        return None, _to_float(amount.group(1))
    return None, None


def normalize_percent(raw: str) -> float | None:
    if not raw:
        return None
    match = PERCENT_RE.search(raw)
    return _to_float(match.group(1)) if match else None


def normalize_date(raw: str) -> str | None:
    # returns an ISO yyyy-mm-dd string regardless of the input format, so
    # comparisons between runs never fail just because the site changed format
    if not raw:
        return None
    text = raw.strip()

    iso = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso:
        return iso.group(1)

    # strip everything up through the recognized phrase (wherever it appears),
    # not just when it's the very first word - "Offer valid until: 12 Dec"
    # should still yield "12 Dec", not leave "Offer" stuck on the front
    cleaned = re.sub(r"^.*?(valid until|valid till|until|till|expires?)\s*:?\s*", "", text, flags=re.I).strip()
    cleaned = cleaned.rstrip(".")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_label(raw: str) -> str:
    # collapses whitespace and strips zero-width/non-breaking spaces so the same
    # hotel name from two runs compares equal even if the markup shifted
    if not raw:
        return ""
    text = raw.replace(" ", " ").replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def dedupe_records(records: list[dict], key_field: str) -> tuple[list[dict], int]:
    # keeps the highest-confidence record per key. returns (records, n_dropped)
    # so callers can report duplicates instead of silently discarding them.
    best: dict[str, dict] = {}
    order: list[str] = []
    dropped = 0

    for record in records:
        key = normalize_label(str(record.get(key_field, "")))
        if key not in best:
            best[key] = record
            order.append(key)
            continue
        dropped += 1
        if record.get("confidence", 0) > best[key].get("confidence", 0):
            best[key] = record

    return [best[k] for k in order], dropped


def _to_float(text: str) -> float | None:
    try:
        return float(text.replace(",", ""))
    except (TypeError, ValueError):
        return None
