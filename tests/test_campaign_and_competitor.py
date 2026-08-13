from datetime import datetime, timezone

from agents.reasoning_loop import compare_campaign_records, compare_competitor_records
from extraction.parsers import extract_campaign_record, extract_competitor_record
from extraction.schemas import CampaignRecord, ChangeType, CompetitorOfferRecord

URL = "http://127.0.0.1:5050/test"
NOW = datetime.now(timezone.utc).isoformat()


def make_campaign(slug, headline, cta="Book Now"):
    return CampaignRecord(
        source_url=URL, slug=slug, headline=headline, cta=cta,
        valid_until="2026-09-01", evidence_snippet="test", confidence=1.0, extracted_at=NOW,
    )


def make_offer(competitor, title, discount_pct):
    return CompetitorOfferRecord(
        source_url=URL, competitor=competitor, offer_title=title, discount_pct=discount_pct,
        evidence_snippet="test", confidence=1.0, extracted_at=NOW,
    )


# --- campaign extraction ---

def test_extracts_campaign_headline_cta_and_validity():
    html = """
    <div class="campaign-hero" data-campaign-slug="monsoon-getaway">
      <div class="headline">Monsoon Getaway - Flat 20% Off</div>
      <div class="valid-until">Valid until 2026-09-09</div>
      <a class="cta-button">Grab Deal</a>
    </div>
    """
    record = extract_campaign_record(html, URL, "monsoon-getaway")
    assert record.headline == "Monsoon Getaway - Flat 20% Off"
    assert record.cta == "Grab Deal"
    assert record.valid_until == "2026-09-09"
    assert record.confidence == 1.0


def test_missing_campaign_card_returns_none():
    html = "<div>Not a campaign page</div>"
    record = extract_campaign_record(html, URL, "nowhere")
    assert record is None


def test_campaign_missing_headline_flagged_low_confidence():
    html = """
    <div class="campaign-hero" data-campaign-slug="broken">
      <a class="cta-button">Grab Deal</a>
    </div>
    """
    record = extract_campaign_record(html, URL, "broken")
    assert record.headline == "Unknown"
    assert record.confidence < 1.0


# --- competitor extraction ---

def test_extracts_competitor_offer_and_discount():
    html = """
    <div class="offer-card" data-competitor-name="RivalTrip">
      <div class="offer-title">Weekend Flash Sale</div>
      <div class="discount">15% Off</div>
    </div>
    """
    record = extract_competitor_record(html, URL, "RivalTrip")
    assert record.offer_title == "Weekend Flash Sale"
    assert record.discount_pct == 15.0
    assert record.confidence == 1.0


def test_missing_offer_card_returns_none():
    html = "<div>Not an offer page</div>"
    record = extract_competitor_record(html, URL, "Nobody")
    assert record is None


def test_competitor_missing_discount_flagged_low_confidence():
    html = """
    <div class="offer-card" data-competitor-name="RivalTrip">
      <div class="offer-title">Weekend Flash Sale</div>
    </div>
    """
    record = extract_competitor_record(html, URL, "RivalTrip")
    assert record.discount_pct is None
    assert record.confidence < 1.0


# --- campaign comparison ---

def test_campaign_new_listing_when_no_prior():
    results = compare_campaign_records([make_campaign("monsoon-getaway", "Flat 20% Off")], [])
    assert results[0].change_type == ChangeType.NEW_LISTING


def test_campaign_copy_change_detected():
    current = [make_campaign("monsoon-getaway", "Flat 25% Off")]
    previous = [make_campaign("monsoon-getaway", "Flat 20% Off")]
    results = compare_campaign_records(current, previous)
    assert results[0].change_type == ChangeType.COPY_CHANGE
    assert results[0].business_relevant is True


def test_campaign_no_change_when_identical():
    current = [make_campaign("monsoon-getaway", "Flat 20% Off")]
    previous = [make_campaign("monsoon-getaway", "Flat 20% Off")]
    results = compare_campaign_records(current, previous)
    assert results[0].change_type == ChangeType.NO_CHANGE
    assert results[0].business_relevant is False


# --- competitor comparison ---

def test_competitor_discount_increase_detected():
    current = [make_offer("RivalTrip", "Weekend Flash Sale", 22)]
    previous = [make_offer("RivalTrip", "Weekend Flash Sale", 15)]
    results = compare_competitor_records(current, previous)
    assert results[0].change_type == ChangeType.DISCOUNT_INCREASE
    assert results[0].delta_pct == 7.0


def test_competitor_small_discount_change_is_no_change():
    current = [make_offer("RivalTrip", "Weekend Flash Sale", 15.5)]
    previous = [make_offer("RivalTrip", "Weekend Flash Sale", 15)]
    results = compare_competitor_records(current, previous)
    assert results[0].change_type == ChangeType.NO_CHANGE


def test_competitor_offer_title_change_detected():
    current = [make_offer("RivalTrip", "Honeymoon Package Discount", 18)]
    previous = [make_offer("RivalTrip", "Weekend Flash Sale", 18)]
    results = compare_competitor_records(current, previous)
    assert results[0].change_type == ChangeType.COPY_CHANGE
