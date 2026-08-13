from agents.completion import generate_summary


def test_no_relevant_changes_but_low_confidence_still_requires_review():
    # regression test: generate_summary()'s early-return branch for "no
    # business-relevant changes" used to hardcode requires_human_review=False
    # without looking at low_confidence_count at all - so a rerun (or any run)
    # whose only extracted record was genuinely low-confidence but happened to
    # match its prior snapshot (change_type=no_change, not business_relevant)
    # would silently skip review, contradicting the engineering guidelines, section 7 ("never
    # convert uncertainty into false certainty").
    summary = generate_summary(
        run_id="run-1", workflow="hotel_pricing_watch", entity_key="Test",
        comparisons=[], low_confidence_count=1,
    )
    assert summary.requires_human_review is True
    assert "low extraction confidence" in summary.confidence_note


def test_no_relevant_changes_and_no_low_confidence_does_not_require_review():
    summary = generate_summary(
        run_id="run-2", workflow="hotel_pricing_watch", entity_key="Test",
        comparisons=[], low_confidence_count=0,
    )
    assert summary.requires_human_review is False
