# post-extraction validation: sanity-checks structured records and returns
# confidence penalties + human-readable notes. separate from parsers.py so the
# rules that decide "is this value plausible?" can be reviewed on their own.
from __future__ import annotations

from datetime import date

# anything outside these ranges is almost certainly a parsing error rather than
# a real value, so flag it instead of trusting it
PRICE_MIN, PRICE_MAX = 100.0, 500_000.0
RATING_MIN, RATING_MAX = 0.0, 5.0
DISCOUNT_MIN, DISCOUNT_MAX = 0.0, 100.0

KNOWN_CURRENCIES = {"INR", "USD", "EUR", "GBP", "AED", "SGD"}


def validate_price(price: float | None, currency: str | None) -> tuple[float, list[str]]:
    penalty, notes = 0.0, []
    if price is None:
        return penalty, notes
    if not (PRICE_MIN <= price <= PRICE_MAX):
        penalty += 0.3
        notes.append(f"Price {price:.0f} outside plausible range {PRICE_MIN:.0f}-{PRICE_MAX:.0f}")
    if currency and currency not in KNOWN_CURRENCIES:
        penalty += 0.1
        notes.append(f"Unrecognized currency code '{currency}'")
    if price is not None and currency is None:
        penalty += 0.1
        notes.append("Price found without a currency code")
    return penalty, notes


def validate_rating(rating: float | None) -> tuple[float, list[str]]:
    if rating is None:
        return 0.0, []
    if not (RATING_MIN <= rating <= RATING_MAX):
        return 0.2, [f"Rating {rating} outside valid range {RATING_MIN}-{RATING_MAX}"]
    return 0.0, []


def validate_discount(discount_pct: float | None) -> tuple[float, list[str]]:
    if discount_pct is None:
        return 0.0, []
    if not (DISCOUNT_MIN <= discount_pct <= DISCOUNT_MAX):
        return 0.3, [f"Discount {discount_pct}% outside valid range 0-100%"]
    return 0.0, []


def validate_valid_until(valid_until: str | None) -> tuple[float, list[str]]:
    # a campaign whose validity date is already in the past is worth flagging -
    # it usually means the page is stale or we parsed the wrong element
    if not valid_until:
        return 0.0, []
    try:
        parsed = date.fromisoformat(valid_until)
    except ValueError:
        return 0.1, [f"Validity date '{valid_until}' is not ISO format"]
    if parsed < date.today():
        return 0.1, [f"Validity date {valid_until} is in the past (possibly stale page)"]
    return 0.0, []


def clamp_confidence(confidence: float) -> float:
    return max(0.0, min(1.0, confidence))


def merge_notes(existing: list[str], new: list[str]) -> list[str]:
    return existing + [n for n in new if n not in existing]
