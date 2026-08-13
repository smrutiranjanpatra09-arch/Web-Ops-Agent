from __future__ import annotations

from extraction.normalizers import normalize_label
from extraction.schemas import (
    CampaignRecord, ChangeType, ComparisonResult, CompetitorOfferRecord, HotelRecord,
    PartnerUpdateRecord, TrendSignalRecord,
)

# ignore price/discount wiggle under this % - otherwise every run "detects" a change
PRICE_CHANGE_THRESHOLD_PCT = 3.0
DISCOUNT_CHANGE_THRESHOLD_PCT = 2.0


def compare_hotel_records(current: list[HotelRecord], previous: list[HotelRecord]) -> list[ComparisonResult]:
    previous_by_name = {r.hotel_name: r for r in previous}
    current_by_name = {r.hotel_name: r for r in current}
    results: list[ComparisonResult] = []

    for name, cur in current_by_name.items():
        prev = previous_by_name.get(name)

        if prev is None:
            results.append(
                ComparisonResult(
                    entity_name=name,
                    entity_key=cur.city,
                    change_type=ChangeType.NEW_LISTING,
                    current_value=_describe_hotel(cur),
                    business_relevant=True,
                )
            )
            continue

        if prev.available and not cur.available:
            results.append(
                ComparisonResult(
                    entity_name=name,
                    entity_key=cur.city,
                    change_type=ChangeType.AVAILABILITY_CHANGE,
                    previous_value="available",
                    current_value="sold out",
                    business_relevant=True,
                )
            )
            continue
        if not prev.available and cur.available:
            results.append(
                ComparisonResult(
                    entity_name=name,
                    entity_key=cur.city,
                    change_type=ChangeType.AVAILABILITY_CHANGE,
                    previous_value="sold out",
                    current_value="available",
                    business_relevant=True,
                )
            )
            continue

        price_comparable = prev.price is not None and cur.price is not None and prev.price > 0
        if price_comparable:
            delta_pct = ((cur.price - prev.price) / prev.price) * 100
            if abs(delta_pct) >= PRICE_CHANGE_THRESHOLD_PCT:
                results.append(
                    ComparisonResult(
                        entity_name=name,
                        entity_key=cur.city,
                        change_type=ChangeType.PRICE_INCREASE if delta_pct > 0 else ChangeType.PRICE_DECREASE,
                        previous_value=f"{prev.currency or ''} {prev.price:.0f}".strip(),
                        current_value=f"{cur.currency or ''} {cur.price:.0f}".strip(),
                        abs_diff=round(cur.price - prev.price, 2),
                        delta_pct=round(delta_pct, 1),
                        business_relevant=True,
                    )
                )
                continue
        elif prev.price != cur.price:
            # one side has a price and the other doesn't (or both missing but
            # differently) - price comparability itself changed, which is worth
            # a signal rather than silently falling through to promo/no-change
            results.append(
                ComparisonResult(
                    entity_name=name,
                    entity_key=cur.city,
                    change_type=ChangeType.AVAILABILITY_CHANGE,
                    previous_value=f"{prev.currency or ''} {prev.price:.0f}".strip() if prev.price else "no price",
                    current_value=f"{cur.currency or ''} {cur.price:.0f}".strip() if cur.price else "no price",
                    business_relevant=True,
                )
            )
            continue

        if normalize_label(prev.promo or "").casefold() != normalize_label(cur.promo or "").casefold():
            results.append(
                ComparisonResult(
                    entity_name=name,
                    entity_key=cur.city,
                    change_type=ChangeType.PROMO_CHANGE,
                    previous_value=prev.promo or "none",
                    current_value=cur.promo or "none",
                    business_relevant=True,
                )
            )
            continue

        results.append(
            ComparisonResult(
                entity_name=name,
                entity_key=cur.city,
                change_type=ChangeType.NO_CHANGE,
                business_relevant=False,
            )
        )

    for name, prev in previous_by_name.items():
        if name not in current_by_name:
            results.append(
                ComparisonResult(
                    entity_name=name,
                    entity_key=prev.city,
                    change_type=ChangeType.REMOVED_LISTING,
                    previous_value=_describe_hotel(prev),
                    business_relevant=True,
                )
            )

    return results


def compare_campaign_records(current: list[CampaignRecord], previous: list[CampaignRecord]) -> list[ComparisonResult]:
    previous_by_slug = {r.slug: r for r in previous}
    results: list[ComparisonResult] = []

    for cur in current:
        prev = previous_by_slug.get(cur.slug)
        if prev is None:
            results.append(
                ComparisonResult(
                    entity_name=cur.slug,
                    entity_key="campaign",
                    change_type=ChangeType.NEW_LISTING,
                    current_value=cur.headline,
                    business_relevant=True,
                )
            )
            continue

        if prev.headline != cur.headline or prev.cta != cur.cta:
            results.append(
                ComparisonResult(
                    entity_name=cur.slug,
                    entity_key="campaign",
                    change_type=ChangeType.COPY_CHANGE,
                    previous_value=f"{prev.headline} ({prev.cta})",
                    current_value=f"{cur.headline} ({cur.cta})",
                    business_relevant=True,
                )
            )
            continue

        results.append(
            ComparisonResult(
                entity_name=cur.slug,
                entity_key="campaign",
                change_type=ChangeType.NO_CHANGE,
                business_relevant=False,
            )
        )

    return results


def compare_competitor_records(
    current: list[CompetitorOfferRecord], previous: list[CompetitorOfferRecord]
) -> list[ComparisonResult]:
    previous_by_competitor = {r.competitor: r for r in previous}
    results: list[ComparisonResult] = []

    for cur in current:
        prev = previous_by_competitor.get(cur.competitor)
        if prev is None:
            results.append(
                ComparisonResult(
                    entity_name=cur.competitor,
                    entity_key="competitor",
                    change_type=ChangeType.NEW_LISTING,
                    current_value=f"{cur.offer_title} ({cur.discount_pct}% off)",
                    business_relevant=True,
                )
            )
            continue

        if prev.offer_title != cur.offer_title:
            results.append(
                ComparisonResult(
                    entity_name=cur.competitor,
                    entity_key="competitor",
                    change_type=ChangeType.COPY_CHANGE,
                    previous_value=prev.offer_title,
                    current_value=cur.offer_title,
                    business_relevant=True,
                )
            )
            continue

        discount_comparable = prev.discount_pct is not None and cur.discount_pct is not None
        if discount_comparable:
            delta_pct = cur.discount_pct - prev.discount_pct
            if abs(delta_pct) >= DISCOUNT_CHANGE_THRESHOLD_PCT:
                results.append(
                    ComparisonResult(
                        entity_name=cur.competitor,
                        entity_key="competitor",
                        change_type=ChangeType.DISCOUNT_INCREASE if delta_pct > 0 else ChangeType.DISCOUNT_DECREASE,
                        previous_value=f"{prev.discount_pct}%",
                        current_value=f"{cur.discount_pct}%",
                        abs_diff=round(delta_pct, 1),
                        delta_pct=round(delta_pct, 1),
                        business_relevant=True,
                    )
                )
                continue
        elif prev.discount_pct != cur.discount_pct:
            results.append(
                ComparisonResult(
                    entity_name=cur.competitor,
                    entity_key="competitor",
                    change_type=ChangeType.DISCOUNT_INCREASE if cur.discount_pct else ChangeType.DISCOUNT_DECREASE,
                    previous_value=f"{prev.discount_pct}%" if prev.discount_pct is not None else "no discount",
                    current_value=f"{cur.discount_pct}%" if cur.discount_pct is not None else "no discount",
                    business_relevant=True,
                )
            )
            continue

        results.append(
            ComparisonResult(
                entity_name=cur.competitor,
                entity_key="competitor",
                change_type=ChangeType.NO_CHANGE,
                business_relevant=False,
            )
        )

    return results


def _describe_hotel(record: HotelRecord) -> str:
    price_part = f"{record.currency or ''} {record.price:.0f}".strip() if record.price else "no price"
    return f"{price_part}, {'available' if record.available else 'sold out'}"


def compare_partner_updates(
    current: list[PartnerUpdateRecord], previous: list[PartnerUpdateRecord]
) -> list[ComparisonResult]:
    previous_by_title = {normalize_label(r.title).casefold(): r for r in previous}
    results: list[ComparisonResult] = []

    for cur in current:
        key = normalize_label(cur.title).casefold()
        prev = previous_by_title.get(key)
        if prev is None:
            results.append(
                ComparisonResult(
                    entity_name=cur.title,
                    entity_key=cur.partner_name,
                    change_type=ChangeType.NEW_LISTING,
                    current_value=cur.body or cur.title,
                    business_relevant=True,
                )
            )
            continue

        if normalize_label(prev.body or "").casefold() != normalize_label(cur.body or "").casefold():
            results.append(
                ComparisonResult(
                    entity_name=cur.title,
                    entity_key=cur.partner_name,
                    change_type=ChangeType.COPY_CHANGE,
                    previous_value=prev.body,
                    current_value=cur.body,
                    business_relevant=True,
                )
            )
            continue

        results.append(
            ComparisonResult(
                entity_name=cur.title,
                entity_key=cur.partner_name,
                change_type=ChangeType.NO_CHANGE,
                business_relevant=False,
            )
        )

    current_titles = {normalize_label(r.title).casefold() for r in current}
    for prev in previous:
        if normalize_label(prev.title).casefold() not in current_titles:
            results.append(
                ComparisonResult(
                    entity_name=prev.title,
                    entity_key=prev.partner_name,
                    change_type=ChangeType.REMOVED_LISTING,
                    previous_value=prev.body or prev.title,
                    business_relevant=True,
                )
            )

    return results


def compare_trend_signals(
    current: list[TrendSignalRecord], previous: list[TrendSignalRecord]
) -> list[ComparisonResult]:
    previous_by_destination = {r.destination: r for r in previous}
    results: list[ComparisonResult] = []

    for cur in current:
        prev = previous_by_destination.get(cur.destination)
        if prev is None:
            results.append(
                ComparisonResult(
                    entity_name=cur.destination,
                    entity_key="trend",
                    change_type=ChangeType.NEW_LISTING,
                    current_value=f"{cur.signal_text} ({cur.direction})",
                    business_relevant=True,
                )
            )
            continue

        if prev.direction != cur.direction:
            results.append(
                ComparisonResult(
                    entity_name=cur.destination,
                    entity_key="trend",
                    change_type=ChangeType.SIGNAL_DIRECTION_CHANGE,
                    previous_value=f"{prev.signal_text} ({prev.direction})",
                    current_value=f"{cur.signal_text} ({cur.direction})",
                    business_relevant=True,
                )
            )
            continue

        if normalize_label(prev.signal_text).casefold() != normalize_label(cur.signal_text).casefold():
            results.append(
                ComparisonResult(
                    entity_name=cur.destination,
                    entity_key="trend",
                    change_type=ChangeType.COPY_CHANGE,
                    previous_value=prev.signal_text,
                    current_value=cur.signal_text,
                    business_relevant=True,
                )
            )
            continue

        results.append(
            ComparisonResult(
                entity_name=cur.destination,
                entity_key="trend",
                change_type=ChangeType.NO_CHANGE,
                business_relevant=False,
            )
        )

    return results
