# edge cases the spec's testing section calls out: inconsistent currency
# formats, ambiguous prices, duplicate records, and implausible values that
# should be flagged rather than trusted.
from datetime import date, timedelta

from extraction import normalizers, validators
from extraction.parsers import extract_hotel_records

URL = "http://127.0.0.1:5050/hotels/Goa"


# --- currency normalization ---

def test_currency_with_code_and_thousands_separator():
    assert normalizers.normalize_currency("INR 6,500") == ("INR", 6500.0)


def test_currency_with_symbol_instead_of_code():
    assert normalizers.normalize_currency("₹6500") == ("INR", 6500.0)


def test_currency_with_decimals():
    assert normalizers.normalize_currency("USD 1,299.50") == ("USD", 1299.50)


def test_bare_amount_has_no_currency_code():
    currency, amount = normalizers.normalize_currency("6500")
    assert currency is None
    assert amount == 6500.0


def test_unparseable_currency_returns_nones():
    assert normalizers.normalize_currency("price on request") == (None, None)


# --- percent + date normalization ---

def test_percent_parsed_from_noisy_text():
    assert normalizers.normalize_percent("Flat 22% Off") == 22.0


def test_dates_in_many_formats_all_normalize_to_iso():
    for raw in ["2026-09-09", "09/09/2026", "09-09-2026", "9 Sep 2026", "September 9, 2026"]:
        assert normalizers.normalize_date(raw) == "2026-09-09", raw


def test_date_with_prefix_text_is_stripped():
    assert normalizers.normalize_date("Valid until 2026-09-09") == "2026-09-09"


def test_garbage_date_returns_none():
    assert normalizers.normalize_date("sometime next year") is None


# --- label normalization ---

def test_label_collapses_whitespace_and_nbsp():
    assert normalizers.normalize_label("Seaside  Grand   Resort\n") == "Seaside Grand Resort"


# --- dedupe ---

def test_dedupe_keeps_highest_confidence_and_reports_drops():
    records = [
        {"hotel_name": "Palm Cove Villas", "confidence": 0.5},
        {"hotel_name": "Palm Cove Villas", "confidence": 0.9},
        {"hotel_name": "Baga Beach Inn", "confidence": 1.0},
    ]
    deduped, dropped = normalizers.dedupe_records(records, "hotel_name")
    assert dropped == 1
    assert len(deduped) == 2
    palm = next(r for r in deduped if r["hotel_name"] == "Palm Cove Villas")
    assert palm["confidence"] == 0.9


def test_duplicate_cards_on_page_are_collapsed_and_noted():
    html = """
    <div class="hotel-card"><div class="hotel-name">Twin Listing</div>
      <div class="price" data-price="4000">INR 4000 / night</div></div>
    <div class="hotel-card"><div class="hotel-name">Twin Listing</div>
      <div class="price" data-price="4000">INR 4000 / night</div></div>
    """
    records = extract_hotel_records(html, URL, "Goa")
    assert len(records) == 1
    assert "duplicate" in (records[0].validation_notes or "").lower()


# --- validators ---

def test_implausible_price_is_penalized():
    penalty, notes = validators.validate_price(9_999_999.0, "INR")
    assert penalty > 0
    assert notes


def test_unknown_currency_code_is_penalized():
    penalty, notes = validators.validate_price(5000.0, "XYZ")
    assert penalty > 0
    assert any("XYZ" in n for n in notes)


def test_price_without_currency_is_penalized():
    penalty, notes = validators.validate_price(5000.0, None)
    assert penalty > 0


def test_out_of_range_rating_is_penalized():
    penalty, notes = validators.validate_rating(9.4)
    assert penalty > 0


def test_out_of_range_discount_is_penalized():
    penalty, notes = validators.validate_discount(250.0)
    assert penalty > 0


def test_past_validity_date_flags_stale_page():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    penalty, notes = validators.validate_valid_until(yesterday)
    assert penalty > 0
    assert any("past" in n.lower() for n in notes)


def test_future_validity_date_is_clean():
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert validators.validate_valid_until(tomorrow) == (0.0, [])


def test_ambiguous_price_format_lowers_confidence_end_to_end():
    # "price on request" is a real pattern on travel sites - it must not be
    # silently read as a number
    html = """
    <div class="hotel-card"><div class="hotel-name">Opaque Pricing Inn</div>
      <div class="price">price on request</div></div>
    """
    records = extract_hotel_records(html, URL, "Goa")
    assert records[0].price is None
    assert records[0].confidence < 1.0
    assert records[0].validation_notes
