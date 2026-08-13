"""Seed the mock site as an allowlisted Source with per-workflow policies.
Without this, every browser navigation is rejected with POLICY_RESTRICTED,
since no browser action may target a domain/URL not present in the Source
registry. Run once after migrations:

    docker compose exec api python -m backend.seed_sources
"""
from backend.app.database.session import SessionLocal
from backend.app.models.source import Source, SourcePolicy

SOURCE_ID = "src-demo"
SOURCE_DOMAIN = "mock-site:5050"

POLICIES = (
    ("pol-hotels", "http://mock-site:5050/hotels/"),
    ("pol-campaign", "http://mock-site:5050/campaign/"),
    ("pol-competitor", "http://mock-site:5050/competitor/"),
    ("pol-partner", "http://mock-site:5050/partner/"),
    ("pol-trends", "http://mock-site:5050/trends"),
)


def main() -> None:
    db = SessionLocal()
    try:
        source = db.get(Source, SOURCE_ID)
        if source is None:
            source = Source(
                id=SOURCE_ID, domain=SOURCE_DOMAIN, category="hotel_pricing_watch",
                owner="Growth", access_type="public", auth_required=False,
                review_required=False, health_state="HEALTHY",
            )
            db.add(source)
            print(f"seeded source {SOURCE_DOMAIN}")
        else:
            print(f"source {SOURCE_DOMAIN} already exists, skipping")

        for policy_id, url_pattern in POLICIES:
            if db.get(SourcePolicy, policy_id) is not None:
                continue
            db.add(SourcePolicy(
                id=policy_id, source_id=SOURCE_ID, url_pattern=url_pattern,
                allowed_actions="navigate,extract,screenshot",
                rate_limit_per_minute=10, timeout_seconds=15, retry_cap=2,
            ))
            print(f"seeded policy {policy_id} ({url_pattern})")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
