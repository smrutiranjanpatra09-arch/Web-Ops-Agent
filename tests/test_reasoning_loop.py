from datetime import datetime, timezone

from agents.reasoning_loop import compare_hotel_records
from extraction.schemas import ChangeType, HotelRecord

NOW = datetime.now(timezone.utc).isoformat()


def make_record(name, price, available=True, promo=None, city="Goa"):
    return HotelRecord(
        source_url="http://test",
        city=city,
        hotel_name=name,
        price=price,
        currency="INR",
        available=available,
        promo=promo,
        rating=4.0,
        evidence_snippet="test",
        confidence=1.0,
        extracted_at=NOW,
    )


def test_new_listing_detected():
    current = [make_record("New Hotel", 5000)]
    previous = []
    results = compare_hotel_records(current, previous)
    assert results[0].change_type == ChangeType.NEW_LISTING
    assert results[0].business_relevant is True


def test_removed_listing_detected():
    current = []
    previous = [make_record("Gone Hotel", 5000)]
    results = compare_hotel_records(current, previous)
    assert results[0].change_type == ChangeType.REMOVED_LISTING
    assert results[0].business_relevant is True


def test_small_price_change_below_threshold_is_no_change():
    current = [make_record("Stable Hotel", 5010)]
    previous = [make_record("Stable Hotel", 5000)]
    results = compare_hotel_records(current, previous)
    assert results[0].change_type == ChangeType.NO_CHANGE
    assert results[0].business_relevant is False


def test_price_increase_above_threshold_flagged():
    current = [make_record("Rising Hotel", 6000)]
    previous = [make_record("Rising Hotel", 5000)]
    results = compare_hotel_records(current, previous)
    assert results[0].change_type == ChangeType.PRICE_INCREASE
    assert results[0].business_relevant is True
    assert results[0].delta_pct == 20.0


def test_price_decrease_above_threshold_flagged():
    current = [make_record("Falling Hotel", 4000)]
    previous = [make_record("Falling Hotel", 5000)]
    results = compare_hotel_records(current, previous)
    assert results[0].change_type == ChangeType.PRICE_DECREASE
    assert results[0].delta_pct == -20.0


def test_availability_change_sold_out_flagged_even_without_price_change():
    current = [make_record("Now Sold Out", None, available=False)]
    previous = [make_record("Now Sold Out", 5000, available=True)]
    results = compare_hotel_records(current, previous)
    assert results[0].change_type == ChangeType.AVAILABILITY_CHANGE
    assert results[0].business_relevant is True


def test_promo_change_flagged():
    current = [make_record("Promo Hotel", 5000, promo="Flash Sale")]
    previous = [make_record("Promo Hotel", 5000, promo=None)]
    results = compare_hotel_records(current, previous)
    assert results[0].change_type == ChangeType.PROMO_CHANGE
    assert results[0].business_relevant is True


def test_no_prior_snapshot_all_treated_as_new():
    current = [make_record("A", 100), make_record("B", 200)]
    results = compare_hotel_records(current, [])
    assert all(r.change_type == ChangeType.NEW_LISTING for r in results)
