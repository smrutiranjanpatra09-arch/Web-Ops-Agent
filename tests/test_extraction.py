from extraction.parsers import extract_hotel_records

GOA_URL = "http://127.0.0.1:5050/hotels/Goa"


def test_extracts_available_hotel_with_price_and_promo():
    html = """
    <div class="hotel-card" data-hotel-name="Test Hotel">
      <div class="hotel-name">Test Hotel</div>
      <div class="rating">Rating: 4.2 / 5</div>
      <div class="price" data-price="4500">INR 4500 / night</div>
      <div class="promo">Early Bird 10% Off</div>
    </div>
    """
    records = extract_hotel_records(html, GOA_URL, "Goa")
    assert len(records) == 1
    r = records[0]
    assert r.hotel_name == "Test Hotel"
    assert r.price == 4500.0
    assert r.currency == "INR"
    assert r.available is True
    assert r.promo == "Early Bird 10% Off"
    assert r.rating == 4.2
    assert r.confidence == 1.0


def test_sold_out_hotel_has_no_price_and_full_confidence():
    html = """
    <div class="hotel-card" data-hotel-name="Sold Out Hotel">
      <div class="hotel-name">Sold Out Hotel</div>
      <div class="rating">Rating: 3.9 / 5</div>
      <div class="unavailable">Sold Out</div>
    </div>
    """
    records = extract_hotel_records(html, GOA_URL, "Goa")
    r = records[0]
    assert r.available is False
    assert r.price is None
    # this is the expected shape for sold out, not a parsing failure
    assert r.confidence == 1.0


def test_ambiguous_card_with_no_price_and_no_sold_out_marker_is_flagged_low_confidence():
    html = """
    <div class="hotel-card" data-hotel-name="Broken Card">
      <div class="hotel-name">Broken Card</div>
    </div>
    """
    records = extract_hotel_records(html, GOA_URL, "Goa")
    r = records[0]
    # no price, no sold-out marker either -> shouldn't just silently assume one or the other
    assert r.available is False
    assert r.price is None
    assert r.confidence < 1.0
    assert r.validation_notes is not None


def test_unparseable_rating_is_flagged_but_does_not_crash():
    html = """
    <div class="hotel-card" data-hotel-name="Weird Rating Hotel">
      <div class="hotel-name">Weird Rating Hotel</div>
      <div class="rating">Excellent stay!</div>
      <div class="price" data-price="3000">INR 3000 / night</div>
    </div>
    """
    records = extract_hotel_records(html, GOA_URL, "Goa")
    r = records[0]
    assert r.rating is None
    assert r.confidence < 1.0


def test_no_hotel_cards_returns_empty_list():
    html = "<div>No listings today.</div>"
    records = extract_hotel_records(html, GOA_URL, "Goa")
    assert records == []


def test_multiple_cards_extracted_independently():
    html = """
    <div class="hotel-card" data-hotel-name="Hotel A">
      <div class="hotel-name">Hotel A</div>
      <div class="price" data-price="1000">INR 1000</div>
    </div>
    <div class="hotel-card" data-hotel-name="Hotel B">
      <div class="hotel-name">Hotel B</div>
      <div class="unavailable">Sold Out</div>
    </div>
    """
    records = extract_hotel_records(html, GOA_URL, "Goa")
    assert len(records) == 2
    assert records[0].hotel_name == "Hotel A"
    assert records[1].available is False
