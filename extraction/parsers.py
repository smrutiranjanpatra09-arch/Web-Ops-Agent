from __future__ import annotations

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from extraction import normalizers, validators
from extraction.schemas import (
    CampaignRecord, CompetitorOfferRecord, HotelRecord, PartnerUpdateRecord, TrendSignalRecord,
)


def extract_hotel_records(html_excerpt: str, source_url: str, city: str) -> list[HotelRecord]:
    soup = BeautifulSoup(html_excerpt, "html.parser")
    cards = soup.select(".hotel-card")
    now = datetime.now(timezone.utc).isoformat()
    records: list[HotelRecord] = []

    for card in cards:
        name_el = card.select_one(".hotel-name")
        raw_name = name_el.get_text(strip=True) if name_el else card.get("data-hotel-name", "Unknown")
        name = normalizers.normalize_label(raw_name) or "Unknown"

        price_el = card.select_one(".price")
        unavailable_el = card.select_one(".unavailable")
        rating_el = card.select_one(".rating")
        promo_el = card.select_one(".promo")

        confidence = 1.0
        notes: list[str] = []

        price = None
        currency = None
        if price_el is not None:
            available = unavailable_el is None
            raw_price_attr = price_el.get("data-price")
            currency, parsed_price = normalizers.normalize_currency(price_el.get_text(strip=True))
            if raw_price_attr:
                # the data-price attribute is authoritative when present
                attr_price = normalizers._to_float(raw_price_attr)
                if attr_price is None:
                    confidence -= 0.2
                    notes.append("data-price attribute was non-numeric")
                else:
                    price = attr_price
            if price is None:
                price = parsed_price
            if price is None:
                confidence -= 0.3
                available = False
                notes.append("Could not parse a price value from card text; availability is unconfirmed")
        elif unavailable_el is not None:
            available = False
        else:
            # no price AND no "sold out" tag - card is just broken/ambiguous,
            # don't pretend we know it's sold out
            available = False
            confidence -= 0.4
            notes.append("No price element or sold-out marker found; availability is ambiguous")

        rating = None
        if rating_el:
            rating_match = re.search(r"([\d.]+)\s*/\s*5", rating_el.get_text())
            if rating_match:
                rating = normalizers._to_float(rating_match.group(1))
            else:
                confidence -= 0.1
                notes.append("Rating text present but unparseable")

        promo = normalizers.normalize_label(promo_el.get_text(strip=True)) if promo_el else None

        # plausibility checks on the normalized values
        for penalty, extra in (validators.validate_price(price, currency),
                               validators.validate_rating(rating)):
            confidence -= penalty
            notes = validators.merge_notes(notes, extra)

        records.append(
            HotelRecord(
                source_url=source_url,
                city=city,
                hotel_name=name,
                price=price,
                currency=currency,
                available=available,
                promo=promo,
                rating=rating,
                evidence_snippet=card.get_text(" ", strip=True)[:300],
                confidence=validators.clamp_confidence(confidence),
                validation_notes="; ".join(notes) if notes else None,
                extracted_at=now,
            )
        )

    # the same hotel appearing twice on one page is a data problem, not a
    # second listing - keep the higher-confidence row and say so
    deduped, dropped = normalizers.dedupe_records(
        [r.model_dump() for r in records], key_field="hotel_name"
    )
    if dropped:
        for row in deduped:
            existing = row.get("validation_notes")
            note = f"{dropped} duplicate listing(s) collapsed for this page"
            row["validation_notes"] = f"{existing}; {note}" if existing else note
    return [HotelRecord(**r) for r in deduped]


def extract_campaign_record(html_excerpt: str, source_url: str, slug: str) -> CampaignRecord | None:
    soup = BeautifulSoup(html_excerpt, "html.parser")
    card = soup.select_one(".campaign-hero")
    if card is None:
        return None

    now = datetime.now(timezone.utc).isoformat()
    confidence = 1.0
    notes: list[str] = []

    headline_el = card.select_one(".headline")
    headline = normalizers.normalize_label(headline_el.get_text(strip=True)) if headline_el else None
    if not headline:
        confidence -= 0.5
        notes.append("No headline element found")
        headline = "Unknown"

    cta_el = card.select_one(".cta-button")
    cta = normalizers.normalize_label(cta_el.get_text(strip=True)) if cta_el else None
    if cta is None:
        confidence -= 0.1
        notes.append("No CTA button found")

    valid_el = card.select_one(".valid-until")
    valid_until = None
    if valid_el:
        valid_until = normalizers.normalize_date(valid_el.get_text())
        if valid_until is None:
            confidence -= 0.1
            notes.append("Validity date present but unparseable")

    penalty, extra = validators.validate_valid_until(valid_until)
    confidence -= penalty
    notes = validators.merge_notes(notes, extra)

    return CampaignRecord(
        source_url=source_url,
        slug=slug,
        headline=headline,
        cta=cta,
        valid_until=valid_until,
        evidence_snippet=card.get_text(" ", strip=True)[:300],
        confidence=validators.clamp_confidence(confidence),
        validation_notes="; ".join(notes) if notes else None,
        extracted_at=now,
    )


def extract_competitor_record(html_excerpt: str, source_url: str, competitor: str) -> CompetitorOfferRecord | None:
    soup = BeautifulSoup(html_excerpt, "html.parser")
    card = soup.select_one(".offer-card")
    if card is None:
        return None

    now = datetime.now(timezone.utc).isoformat()
    confidence = 1.0
    notes: list[str] = []

    title_el = card.select_one(".offer-title")
    title = normalizers.normalize_label(title_el.get_text(strip=True)) if title_el else None
    if not title:
        confidence -= 0.5
        notes.append("No offer title element found")
        title = "Unknown"

    discount_el = card.select_one(".discount")
    discount_pct = None
    if discount_el:
        discount_pct = normalizers.normalize_percent(discount_el.get_text())
        if discount_pct is None:
            confidence -= 0.3
            notes.append("Discount text present but unparseable")
    else:
        confidence -= 0.4
        notes.append("No discount element found")

    penalty, extra = validators.validate_discount(discount_pct)
    confidence -= penalty
    notes = validators.merge_notes(notes, extra)

    return CompetitorOfferRecord(
        source_url=source_url,
        competitor=competitor,
        offer_title=title,
        discount_pct=discount_pct,
        evidence_snippet=card.get_text(" ", strip=True)[:300],
        confidence=validators.clamp_confidence(confidence),
        validation_notes="; ".join(notes) if notes else None,
        extracted_at=now,
    )


def extract_partner_updates(html_excerpt: str, source_url: str, partner_name: str) -> list[PartnerUpdateRecord]:
    soup = BeautifulSoup(html_excerpt, "html.parser")
    items = soup.select(".update-item")
    now = datetime.now(timezone.utc).isoformat()
    records: list[PartnerUpdateRecord] = []

    for item in items:
        confidence = 1.0
        notes: list[str] = []

        title_el = item.select_one(".update-title")
        title = normalizers.normalize_label(title_el.get_text(strip=True)) if title_el else None
        if not title:
            confidence -= 0.5
            notes.append("No update title element found")
            title = "Unknown"

        body_el = item.select_one(".update-body")
        body = normalizers.normalize_label(body_el.get_text(strip=True)) if body_el else None
        if body is None:
            confidence -= 0.2
            notes.append("No update body found")

        records.append(
            PartnerUpdateRecord(
                source_url=source_url,
                partner_name=partner_name,
                title=title,
                body=body,
                evidence_snippet=item.get_text(" ", strip=True)[:300],
                confidence=validators.clamp_confidence(confidence),
                validation_notes="; ".join(notes) if notes else None,
                extracted_at=now,
            )
        )

    # same update title appearing twice on one page is a rendering problem,
    # not two separate updates - keep the higher-confidence row
    deduped, dropped = normalizers.dedupe_records([r.model_dump() for r in records], key_field="title")
    if dropped:
        for row in deduped:
            existing = row.get("validation_notes")
            note = f"{dropped} duplicate update(s) collapsed for this page"
            row["validation_notes"] = f"{existing}; {note}" if existing else note
    return [PartnerUpdateRecord(**r) for r in deduped]


def extract_trend_signals(html_excerpt: str, source_url: str, scope: str) -> list[TrendSignalRecord]:
    soup = BeautifulSoup(html_excerpt, "html.parser")
    items = soup.select(".trend-item")
    now = datetime.now(timezone.utc).isoformat()
    records: list[TrendSignalRecord] = []

    for item in items:
        confidence = 1.0
        notes: list[str] = []

        destination = item.get("data-destination")
        if not destination:
            name_el = item.select_one(".hotel-name")
            destination = normalizers.normalize_label(name_el.get_text(strip=True)) if name_el else None
        if not destination:
            confidence -= 0.5
            notes.append("No destination found")
            destination = "Unknown"

        signal_el = item.select_one(".room-type")
        signal_text = normalizers.normalize_label(signal_el.get_text(strip=True)) if signal_el else None
        if not signal_text:
            confidence -= 0.4
            notes.append("No signal text found")
            signal_text = ""

        direction_el = item.select_one(".trend-signal")
        direction = None
        if direction_el:
            classes = direction_el.get("class", [])
            if "trend-up" in classes:
                direction = "up"
            elif "trend-down" in classes:
                direction = "down"
        if direction is None:
            confidence -= 0.2
            notes.append("No trend direction found")

        records.append(
            TrendSignalRecord(
                source_url=source_url,
                destination=destination,
                signal_text=signal_text,
                direction=direction,
                evidence_snippet=item.get_text(" ", strip=True)[:300],
                confidence=validators.clamp_confidence(confidence),
                validation_notes="; ".join(notes) if notes else None,
                extracted_at=now,
            )
        )

    deduped, dropped = normalizers.dedupe_records([r.model_dump() for r in records], key_field="destination")
    if dropped:
        for row in deduped:
            existing = row.get("validation_notes")
            note = f"{dropped} duplicate destination(s) collapsed for this page"
            row["validation_notes"] = f"{existing}; {note}" if existing else note
    return [TrendSignalRecord(**r) for r in deduped]
