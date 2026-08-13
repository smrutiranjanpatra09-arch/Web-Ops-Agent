from extraction.parsers import extract_partner_updates, extract_trend_signals

SOURCE_URL = "http://127.0.0.1:5050/partner/Test%20Partner"


def test_extracts_multiple_partner_updates():
    html = """
    <div class="update-list" data-partner-name="Coastal Resorts Group">
      <div class="update-item">
        <div class="update-title">5 new properties added to Goa inventory</div>
        <div class="update-body">Onboarded 5 new boutique properties across Candolim.</div>
      </div>
      <div class="update-item">
        <div class="update-title">Rate parity update for peak season</div>
        <div class="update-body">Peak season rates now require 15-day notice.</div>
      </div>
    </div>
    """
    records = extract_partner_updates(html, SOURCE_URL, "Coastal Resorts Group")
    assert len(records) == 2
    assert records[0].title == "5 new properties added to Goa inventory"
    assert records[0].body == "Onboarded 5 new boutique properties across Candolim."
    assert records[0].confidence == 1.0
    assert records[1].title == "Rate parity update for peak season"


def test_partner_update_missing_title_flags_low_confidence():
    html = """
    <div class="update-item">
      <div class="update-body">Some update with no title.</div>
    </div>
    """
    records = extract_partner_updates(html, SOURCE_URL, "Test Partner")
    assert len(records) == 1
    assert records[0].title == "Unknown"
    assert records[0].confidence < 1.0
    assert "title" in records[0].validation_notes.lower()


def test_partner_updates_dedupes_identical_titles():
    html = """
    <div class="update-item">
      <div class="update-title">Duplicate Update</div>
      <div class="update-body">First copy.</div>
    </div>
    <div class="update-item">
      <div class="update-title">Duplicate Update</div>
      <div class="update-body">Second copy.</div>
    </div>
    """
    records = extract_partner_updates(html, SOURCE_URL, "Test Partner")
    assert len(records) == 1
    assert "duplicate" in records[0].validation_notes.lower()


def test_no_updates_returns_empty_list():
    records = extract_partner_updates("<div>nothing here</div>", SOURCE_URL, "Test Partner")
    assert records == []


def test_extracts_multiple_trend_signals_with_direction():
    html = """
    <div class="trend-list" data-page="trends">
      <div class="trend-item" data-destination="Goa">
        <div><div class="hotel-name">Goa</div><div class="room-type">Search volume up 18%</div></div>
        <div class="trend-signal trend-up">&#9650;</div>
      </div>
      <div class="trend-item" data-destination="Manali">
        <div><div class="hotel-name">Manali</div><div class="room-type">Lead time dropped</div></div>
        <div class="trend-signal trend-down">&#9660;</div>
      </div>
    </div>
    """
    records = extract_trend_signals(html, SOURCE_URL, "all-destinations")
    assert len(records) == 2
    assert records[0].destination == "Goa"
    assert records[0].direction == "up"
    assert records[0].signal_text == "Search volume up 18%"
    assert records[1].destination == "Manali"
    assert records[1].direction == "down"


def test_trend_signal_missing_direction_flags_low_confidence():
    html = """
    <div class="trend-item" data-destination="Jaipur">
      <div><div class="hotel-name">Jaipur</div><div class="room-type">Some signal text</div></div>
    </div>
    """
    records = extract_trend_signals(html, SOURCE_URL, "all-destinations")
    assert len(records) == 1
    assert records[0].direction is None
    assert records[0].confidence < 1.0


def test_trend_signal_handles_long_signal_text_without_truncation():
    # regression test for the real bug found live in Phase 13: extraction
    # must receive the FULL page HTML, not a caller-truncated snippet - this
    # test only proves the parser itself handles long text correctly; the
    # orchestrator-level fix (full_html threading) is covered by the live
    # integration test in test_integration.py.
    long_text = "Wedding-season inquiries up 34% year-over-year, driven by destination weddings"
    html = f"""
    <div class="trend-item" data-destination="Udaipur">
      <div><div class="hotel-name">Udaipur</div><div class="room-type">{long_text}</div></div>
      <div class="trend-signal trend-up">&#9650;</div>
    </div>
    """
    records = extract_trend_signals(html, SOURCE_URL, "all-destinations")
    assert len(records) == 1
    assert records[0].signal_text == long_text
    assert records[0].direction == "up"
