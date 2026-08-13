# deterministic significance classification and noise filtering
# (MASTER_SPEC section 11) - pure unit tests, no DB needed.
from intelligence.significance.engine import classify_significance, is_noise


def test_below_one_percent_is_insignificant():
    assert classify_significance(0.5) == "insignificant"
    assert classify_significance(-0.9) == "insignificant"


def test_one_to_five_percent_is_minor():
    assert classify_significance(1.0) == "minor"
    assert classify_significance(4.9) == "minor"
    assert classify_significance(-3.0) == "minor"


def test_five_to_fifteen_percent_is_notable():
    assert classify_significance(5.0) == "notable"
    assert classify_significance(14.9) == "notable"


def test_above_fifteen_percent_is_significant():
    assert classify_significance(15.0) == "significant"
    assert classify_significance(24.0) == "significant"
    assert classify_significance(-30.0) == "significant"


def test_none_delta_is_insignificant():
    assert classify_significance(None) == "insignificant"


def test_metadata_fields_are_noise():
    noise, reason = is_noise("extracted_at", "2026-01-01", "2026-01-02")
    assert noise is True
    assert reason


def test_case_and_whitespace_only_difference_is_noise():
    noise, _ = is_noise("promo_change", "10% off", "10%  OFF")
    assert noise is True


def test_genuine_value_change_is_not_noise():
    noise, reason = is_noise("price_increase", "INR 5000", "INR 6200")
    assert noise is False
    assert reason is None


def test_none_values_are_not_flagged_as_noise():
    noise, _ = is_noise("new_listing", None, "INR 5000")
    assert noise is False
