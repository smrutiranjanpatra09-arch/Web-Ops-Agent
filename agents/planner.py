from __future__ import annotations

from extraction.schemas import AgentPlan, BrowserStep

WORKFLOW_SELECTORS = {
    "hotel_pricing_watch": (".hotel-card", ["hotel_name", "price", "currency", "available", "promo", "rating"]),
    "campaign_page_monitoring": (".campaign-hero", ["headline", "cta", "valid_until"]),
    "competitor_offer_tracking": (".offer-card", ["offer_title", "discount_pct"]),
    "partner_update_review": (".update-item", ["title", "body"]),
    "travel_trend_scanning": (".trend-item", ["destination", "signal_text", "direction"]),
}

PLANNER_SYSTEM_PROMPT = """You are the planning module of a governed web operations \
agent for MakeMyTrip. Given a task objective, a target city/entity, and the exact \
allowed target page, produce a JSON browsing plan. You MUST return ONLY valid JSON \
matching this shape, no prose:

{
  "objective": "...",
  "target_urls": ["..."],
  "steps": [{"action": "...", "target": "...", "notes": "..."}],
  "expected_fields": ["..."],
  "stop_conditions": ["..."],
  "risk_notes": "..."
}

Rules:
- Only ever target the single allowed target page given in the user message. Never
  invent other pages or external domains.
- One step must be action="wait_for_selector" with target set to the CSS selector
  given in the user message for this workflow.
- stop_conditions should mention what should halt the run (e.g. page not found,
  expected selector not present, more than 2 consecutive extraction failures).
"""


def build_plan(objective: str, entity_key: str, base_url: str, target_url: str,
                workflow: str = "hotel_pricing_watch", run_id: str | None = None) -> AgentPlan:
    # if the LLM call fails (no key, rate limit, etc) fall back to a hardcoded
    # plan so the rest of the pipeline still runs
    selector, expected_fields = WORKFLOW_SELECTORS.get(workflow, WORKFLOW_SELECTORS["hotel_pricing_watch"])
    try:
        from agents.llm import call_structured

        user_prompt = (
            f"Task objective: {objective}\n"
            f"Entity: {entity_key}\n"
            f"Allowed base URL: {base_url}\n"
            f"Allowed target page: {target_url}\n"
            f"CSS selector to wait for: {selector}\n"
        )
        raw = call_structured(
            PLANNER_SYSTEM_PROMPT, user_prompt,
            node="planner", purpose=f"Generate browser plan for {entity_key}", run_id=run_id,
        )
        return AgentPlan(**raw)
    except Exception:
        return AgentPlan(
            objective=objective,
            target_urls=[target_url],
            steps=[
                BrowserStep(action="navigate", target=target_url, notes="Open target page"),
                BrowserStep(action="wait_for_selector", target=selector, notes="Wait for content to render"),
                BrowserStep(action="extract", target=selector, notes="Extract structured data"),
            ],
            expected_fields=expected_fields,
            stop_conditions=[
                "Target page returns non-200 status",
                f"No {selector} elements found after wait",
                "More than 2 consecutive extraction failures",
            ],
            risk_notes="Fallback deterministic plan used (LLM planning unavailable).",
        )
