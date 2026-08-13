# Disclosed, safe browsing target for the agent's real Playwright execution -
# not a fabricated data source: the HTML/screenshots this site produces are
# genuinely rendered pages, and the browser genuinely navigates/scrapes them.
# /reset regenerates prices so the comparison step has something to detect
# between runs. Covers all 5 journeys from the product spec (hotel pricing,
# competitor offers, campaign pages, partner updates, travel trend signals).
import json
import random
from pathlib import Path

from flask import Flask, render_template

app = Flask(__name__)

STATE_PATH = Path(__file__).parent / "state.json"

CITIES = ["Goa", "Jaipur", "Manali", "Udaipur", "Rishikesh"]

CITY_LABELS = {
    "Goa": "Goa, India",
    "Jaipur": "Jaipur, Rajasthan",
    "Manali": "Manali, Himachal Pradesh",
    "Udaipur": "Udaipur, Rajasthan",
    "Rishikesh": "Rishikesh, Uttarakhand",
}

# hue used to generate a distinct CSS-gradient "photo" per hotel, and a
# per-city photo hue range so cards feel visually themed without any external
# image downloads (keeps the site fully offline/reproducible)
CITY_HUE_RANGE = {
    "Goa": (180, 210),        # sea blues/teals
    "Jaipur": (20, 45),       # sandstone/terracotta
    "Manali": (200, 230),     # mountain blues
    "Udaipur": (280, 320),    # palace purples/pinks
    "Rishikesh": (95, 140),   # riverside greens
}

CITY_THEMES = {
    "Goa": ["Seaside", "Palm Cove", "Baga Beach", "Candolim", "Anjuna", "Calangute",
            "Vagator", "Morjim", "Arossim", "Colva", "Miramar", "Dona Paula",
            "Sinquerim", "Betalbatim", "Cavelossim", "Majorda", "Arpora",
            "Fort Aguada", "Bogmalo", "Utorda", "Benaulim", "Varca", "Mandrem"],
    "Jaipur": ["Pink City", "Amber Fort", "Rajputana", "Hawa Mahal", "City Palace",
               "Nahargarh", "Jal Mahal", "Malviya Nagar", "C-Scheme", "Vaishali Nagar",
               "Bani Park", "Tonk Road", "Sanganer", "Mansarovar", "Jagatpura",
               "Civil Lines", "Raja Park", "Sodala", "Vidhyadhar Nagar",
               "Jawahar Circle", "Ajmer Road", "Durgapura", "Shastri Nagar"],
    "Manali": ["Snow Valley", "Riverfront", "Solang Ridge", "Old Manali", "Vashisht",
               "Hadimba", "Naggar", "Kullu Valley", "Rohtang", "Manikaran",
               "Aleo", "Bahang", "Kasol Road", "Prini", "Simsa", "Burua",
               "Gulaba", "Palchan", "Jagatsukh", "Kothi", "Sethan",
               "Dobhi", "Rangri"],
    "Udaipur": ["Lake Pichola", "City Palace View", "Fatehsagar", "Jagdish Chowk",
                "Hathi Pol", "Ambrai Ghat", "Chandpole", "Sajjangarh", "Badi Lake",
                "Sukhadia Circle", "Bapu Bazaar", "Saheliyon Ki Bari", "Ghanta Ghar",
                "Delhi Gate", "Panna Dhai Park", "Titardi", "Bedla", "Bhuwana"],
    "Rishikesh": ["Laxman Jhula", "Ram Jhula", "Tapovan", "Ganga Ghat", "Swarg Ashram",
                  "Shivpuri", "Byasi", "Muni Ki Reti", "Tapovan Kunj", "Neelkanth Road",
                  "Rishikund", "Gita Bhawan", "Triveni Ghat", "Kailash Gate", "Phool Chatti"],
}

PROPERTY_SUFFIXES = [
    "Grand Resort", "Villas", "Inn", "Heritage Stay", "Suites", "Palace Hotel",
    "Retreat", "Lodge", "Boutique Hotel", "Residency", "Cottage", "Manor",
]

ROOM_TYPES = ["Deluxe Room", "Premium Room", "Suite", "Cottage Room", "Riverside Room", "Standard Room"]


def _build_hotel_catalog():
    catalog = {}
    base_prices = {}
    room_types = {}
    rng = random.Random(42)  # deterministic base catalog across restarts
    for city, themes in CITY_THEMES.items():
        names = []
        for i, theme in enumerate(themes):
            suffix = PROPERTY_SUFFIXES[i % len(PROPERTY_SUFFIXES)]
            name = f"{theme} {suffix}"
            names.append(name)
            base_prices[name] = rng.randint(28, 85) * 100
            room_types[name] = ROOM_TYPES[i % len(ROOM_TYPES)]
        catalog[city] = names
    return catalog, base_prices, room_types


HOTELS, BASE_PRICES, ROOM_TYPE_BY_HOTEL = _build_hotel_catalog()

CAMPAIGN_PAGES = ["monsoon-getaway", "festive-flight-deals", "republic-day-sale"]

CAMPAIGN_CONTENT = {
    "monsoon-getaway": {
        "placement": "Homepage Hero Banner",
        "headlines": [
            {"headline": "Monsoon Getaway — Flat 20% Off Hill Stations", "cta": "Book Now",
             "offer_copy": "Escape the heat. Save big on Manali, Rishikesh and hill-station stays booked this week."},
            {"headline": "Monsoon Getaway — Flat 25% Off Hill Stations", "cta": "Grab Deal",
             "offer_copy": "Our biggest monsoon discount yet — 25% off hill-station hotels, limited rooms."},
            {"headline": "Monsoon Getaway — Buy 1 Get 1 Night Free", "cta": "Explore Offers",
             "offer_copy": "Book 2 nights, pay for 1 at select hill-station partner hotels."},
        ],
    },
    "festive-flight-deals": {
        "placement": "Search Results Interstitial",
        "headlines": [
            {"headline": "Festive Flight Deals — Up to ₹3,000 Off", "cta": "Book Now",
             "offer_copy": "Combine flights and hotels this festive season and save up to ₹3,000 per booking."},
            {"headline": "Festive Flight Deals — Up to ₹4,500 Off", "cta": "Grab Deal",
             "offer_copy": "Extended festive pricing — save up to ₹4,500 on combo bookings, ends soon."},
            {"headline": "Festive Flight Deals — Free Meal Upgrade", "cta": "Explore Offers",
             "offer_copy": "Every festive booking now includes a complimentary meal upgrade."},
        ],
    },
    "republic-day-sale": {
        "placement": "App Banner",
        "headlines": [
            {"headline": "Republic Day Sale — 26% Off Everything", "cta": "Book Now",
             "offer_copy": "One day only: 26% off hotels, homestays and packages across India."},
            {"headline": "Republic Day Sale — 26% Off + Free Cancellation", "cta": "Grab Deal",
             "offer_copy": "26% off plus free cancellation on all Republic Day bookings."},
        ],
    },
}

COMPETITORS = ["RivalTrip", "OtherBooking", "QuickStay"]

COMPETITOR_OFFERS_POOL = {
    "RivalTrip": [
        {"title": "Weekend Flash Sale", "discount": 15, "terms": "Valid Fri-Sun, select cities only."},
        {"title": "Weekend Flash Sale", "discount": 22, "terms": "Valid Fri-Sun, extended to all cities."},
        {"title": "Honeymoon Package Discount", "discount": 18, "terms": "Couples only, min 2-night stay."},
    ],
    "OtherBooking": [
        {"title": "Member Exclusive Rates", "discount": 10, "terms": "Loyalty members only."},
        {"title": "Member Exclusive Rates", "discount": 12, "terms": "Loyalty members only, tier 2+."},
        {"title": "Last Minute Deals", "discount": 30, "terms": "Bookings within 48 hours of check-in."},
    ],
    "QuickStay": [
        {"title": "New User Discount", "discount": 20, "terms": "First booking only."},
        {"title": "New User Discount", "discount": 25, "terms": "First booking only, app exclusive."},
        {"title": "Business Travel Rates", "discount": 14, "terms": "Corporate account required."},
    ],
}

PARTNER_NAMES = ["Coastal Resorts Group", "Rajasthan Heritage Hotels", "Himalayan Stays Co-op"]

PARTNER_UPDATE_POOL = {
    "Coastal Resorts Group": [
        {"title": "Updated cancellation policy for all Goa properties",
         "body": "Free cancellation window reduced from 48h to 24h before check-in, effective immediately."},
        {"title": "5 new properties added to Goa inventory",
         "body": "Coastal Resorts Group has onboarded 5 new boutique properties across Candolim and Anjuna."},
        {"title": "Rate parity update for peak season",
         "body": "Peak season (Dec-Jan) rates now require 15-day advance notice for any adjustment."},
    ],
    "Rajasthan Heritage Hotels": [
        {"title": "Heritage property renovation completed in Jaipur",
         "body": "The City Palace View property has completed renovations; new photos and amenities live."},
        {"title": "Group rate contract renewed for 2026-27",
         "body": "Commission structure unchanged; new minimum-stay requirement of 2 nights during festivals."},
    ],
    "Himalayan Stays Co-op": [
        {"title": "Winter closure notice for 3 Manali properties",
         "body": "3 high-altitude properties will close for winter maintenance from January 15 to March 1."},
        {"title": "New adventure-package bundling available",
         "body": "Co-op properties now support bundled adventure-activity packages at checkout."},
    ],
}

TREND_SIGNALS = [
    {"destination": "Goa", "signal": "Search volume up 18% week-over-week", "direction": "up"},
    {"destination": "Manali", "signal": "Average booking lead time dropped to 6 days", "direction": "down"},
    {"destination": "Jaipur", "signal": "Weekend occupancy up 9% vs last month", "direction": "up"},
    {"destination": "Udaipur", "signal": "Wedding-season inquiries up 34% year-over-year", "direction": "up"},
    {"destination": "Rishikesh", "signal": "Average daily rate down 5% amid new inventory", "direction": "down"},
]


def _load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except json.JSONDecodeError:
            return None
    return None


def _generate_state():
    state = {"cities": {}, "campaigns": {}, "competitors": {}, "partners": {}, "trends": []}
    for city in CITIES:
        hotels = []
        for name in HOTELS[city]:
            base = BASE_PRICES[name]
            drift_pct = random.uniform(-0.15, 0.20)
            price = round(base * (1 + drift_pct), -1)
            available = random.random() > 0.12
            promo = random.random() > 0.65
            hotels.append(
                {
                    "name": name,
                    "price": int(price),
                    "currency": "INR",
                    "available": available,
                    "promo": "Early Bird 10% Off" if promo else None,
                    "rating": round(random.uniform(3.6, 4.8), 1),
                    "room_type": ROOM_TYPE_BY_HOTEL[name],
                    "stay_date": "2026-12-20",
                    "occupancy": "2 Adults",
                    "hue": hash(name) % 40,
                }
            )
        state["cities"][city] = hotels

    for slug in CAMPAIGN_PAGES:
        content = CAMPAIGN_CONTENT[slug]
        chosen = random.choice(content["headlines"])
        state["campaigns"][slug] = {
            **chosen,
            "placement": content["placement"],
            "valid_until": f"2026-{random.randint(8, 12):02d}-{random.randint(1, 28):02d}",
        }

    for competitor in COMPETITORS:
        offer = random.choice(COMPETITOR_OFFERS_POOL[competitor])
        state["competitors"][competitor] = {
            "title": offer["title"],
            "discount": offer["discount"],
            "terms": offer["terms"],
        }

    for partner in PARTNER_NAMES:
        state["partners"][partner] = random.sample(
            PARTNER_UPDATE_POOL[partner], k=min(2, len(PARTNER_UPDATE_POOL[partner]))
        )

    state["trends"] = TREND_SIGNALS

    return state


def _save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def get_state(regenerate: bool = False):
    if regenerate:
        state = _generate_state()
        _save_state(state)
        return state
    state = _load_state()
    if state is None or "partners" not in state or "trends" not in state:
        # missing keys means this is a state.json from before those were added
        state = _generate_state()
        _save_state(state)
    return state


@app.route("/")
def index():
    state = get_state()
    return render_template(
        "index.html", cities=CITIES, city_labels=CITY_LABELS,
        campaigns=CAMPAIGN_PAGES, competitors=COMPETITORS, partners=PARTNER_NAMES,
    )


@app.route("/hotels/<city>")
def hotels(city):
    state = get_state()
    hotels_for_city = state["cities"].get(city, [])
    return render_template(
        "hotels.html", city=city, city_label=CITY_LABELS.get(city, city),
        hotels=hotels_for_city, hue_range=CITY_HUE_RANGE.get(city, (200, 230)),
    )


@app.route("/campaign/<slug>")
def campaign(slug):
    state = get_state()
    data = state["campaigns"].get(slug)
    if data is None:
        return "Campaign not found", 404
    return render_template("campaign.html", slug=slug, campaign=data)


@app.route("/competitor/<name>")
def competitor(name):
    state = get_state()
    data = state["competitors"].get(name)
    if data is None:
        return "Competitor not found", 404
    return render_template("competitor.html", name=name, offer=data)


@app.route("/partner/<name>")
def partner(name):
    state = get_state()
    updates = state["partners"].get(name)
    if updates is None:
        return "Partner not found", 404
    return render_template("partner.html", name=name, updates=updates)


# Fixed pixel positions for the 5 demo destinations on the static trends
# map (mock_site/templates/trends.html). Purely cosmetic layout coordinates
# for an inline SVG - not geographic data, just stylized placement within
# the 300x320 canvas.
TREND_MAP_POSITIONS = {
    "Goa": (90, 230),
    "Manali": (170, 40),
    "Jaipur": (150, 110),
    "Udaipur": (110, 150),
    "Rishikesh": (190, 70),
}


@app.route("/trends")
def trends():
    state = get_state()
    trends_with_positions = [
        {**t, "map_x": TREND_MAP_POSITIONS.get(t["destination"], (150, 160))[0],
         "map_y": TREND_MAP_POSITIONS.get(t["destination"], (150, 160))[1]}
        for t in state["trends"]
    ]
    return render_template("trends.html", trends=trends_with_positions)


@app.route("/reset")
def reset():
    # hit this between runs to simulate a day passing / prices moving
    state = get_state(regenerate=True)
    return {"status": "regenerated", "cities": list(state["cities"].keys())}


if __name__ == "__main__":
    # host/port come from env so the same file works locally (127.0.0.1) and
    # inside a container, where it has to bind 0.0.0.0 to be reachable
    import os

    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "5050"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
