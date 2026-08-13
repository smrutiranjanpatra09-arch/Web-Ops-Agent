from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy.orm import Session

from backend.app.models.source import Source, SourcePolicy


class PolicyViolation(Exception):
    pass


def check_domain_allowed(db: Session, target_url: str) -> Source:
    # no browser action may target a domain/URL not present in the source
    # registry (MASTER_SPEC section 28) - this is the enforcement point.
    domain = urlparse(target_url).netloc
    source = db.query(Source).filter(Source.domain == domain).one_or_none()
    if source is None:
        raise PolicyViolation(f"Domain '{domain}' is not in the approved source registry.")
    if source.health_state == "REVIEW_REQUIRED":
        raise PolicyViolation(f"Source '{domain}' requires human review before further browsing.")
    return source


def check_action_allowed(policy: SourcePolicy, action: str) -> None:
    allowed = {a.strip() for a in policy.allowed_actions.split(",")}
    if action not in allowed:
        raise PolicyViolation(f"Action '{action}' is not permitted by policy for this source.")


def resolve_policy(db: Session, source: Source, target_url: str) -> SourcePolicy:
    for policy in source.policies:
        if target_url.startswith(policy.url_pattern.rstrip("*")):
            return policy
    raise PolicyViolation(f"No policy matches target URL '{target_url}' for source '{source.domain}'.")
