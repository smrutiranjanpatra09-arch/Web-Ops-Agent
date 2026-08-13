from __future__ import annotations

from datetime import datetime, timezone

from extraction.schemas import ComparisonResult, RunSummary, SignalNarrative
from intelligence.signals.context_builder import summarize_historical_context

COMPLETION_SYSTEM_PROMPT = """You are the completion module of a governed web \
operations agent for MakeMyTrip. Given a list of business-relevant changes detected \
for a recurring web monitoring run, write a concise operational summary. Return ONLY \
JSON matching this shape:

{
  "headline": "one sentence, what changed and why it matters",
  "key_changes": ["short bullet per relevant change"],
  "recommended_owner": "which team should act (e.g. Growth, Revenue Management, Merchandising)",
  "confidence_note": "one sentence noting any uncertainty or low-confidence data",
  "requires_human_review": true or false
}

Only mark requires_human_review true if changes are large (>15% price/discount movement),
ambiguous, or based on low-confidence extraction."""


SIGNAL_NARRATIVE_SYSTEM_PROMPT = """You are the signal-narration module of a governed \
web operations agent for MakeMyTrip. You are given one already-detected, already- \
computed change plus deterministic historical-frequency facts about that entity/field. \
Do NOT recompute or restate raw numbers as if you calculated them - only narrate the \
given facts in plain operational language. Return ONLY JSON matching this shape:

{
  "headline": "one sentence, what changed and why it matters",
  "business_impact": "2-4 sentences explaining the business impact, grounded only in the given facts",
  "historical_context": "one sentence restating the given historical_context fact naturally",
  "recommended_action": "one concrete next step",
  "suggested_owner": "a role, e.g. Revenue Management, Growth, Merchandising - never a person's name",
  "confidence_rationale": "one sentence on why confidence is high/low, referencing the given evidence quality",
  "risk_note": "one sentence on risk, or null if none"
}"""


def generate_signal_narrative(*, change: ComparisonResult, signal_context: dict,
                               evidence_confidence: float, run_id: str | None = None,
                               change_id: str | None = None) -> SignalNarrative:
    # signal_context comes from intelligence/signals/context_builder.py -
    # already-computed frequency/direction facts (engineering guidelines, section 6: the
    # LLM never computes diffs/frequency itself, it only narrates them).
    historical_context_fact = summarize_historical_context(signal_context)

    try:
        from agents.llm import active_provider, call_structured

        provider = active_provider()
        user_prompt = (
            f"Entity: {change.entity_name} ({change.entity_key})\n"
            f"Change type: {change.change_type.value}\n"
            f"Previous value: {change.previous_value}\n"
            f"Current value: {change.current_value}\n"
            f"Delta %: {change.delta_pct}\n"
            f"Extraction confidence: {evidence_confidence}\n"
            f"Historical fact (already computed, do not recalculate): {historical_context_fact}\n"
            f"Occurrences of this change type in recent history: {signal_context['occurrence_count_same_type']}\n"
            f"Direction streak: {signal_context['direction_streak']}\n"
        )
        raw = call_structured(
            SIGNAL_NARRATIVE_SYSTEM_PROMPT, user_prompt,
            node="signal_narrative", purpose=f"Narrate {change.change_type.value} for {change.entity_name}",
            run_id=run_id,
            input_ref_ids={"change_id": change_id} if change_id else None,
        )
        return SignalNarrative(generated_by=provider or "deterministic", **raw)
    except Exception:
        return SignalNarrative(
            generated_by="deterministic",
            headline=f"{change.entity_name}: {change.change_type.value} detected.",
            business_impact=(
                f"{change.entity_name} moved from {change.previous_value} to {change.current_value} "
                f"({change.change_type.value})."
            ),
            historical_context=historical_context_fact,
            recommended_action="Review the change and confirm it reflects an intended update.",
            suggested_owner="Growth",
            confidence_rationale=(
                f"Extraction confidence was {evidence_confidence:.2f}; deterministic fallback narrative used "
                "(no LLM narration available)."
            ),
            risk_note=None,
        )


def generate_summary(run_id: str, workflow: str, entity_key: str, comparisons: list[ComparisonResult],
                      low_confidence_count: int = 0, change_ids: list[str] | None = None) -> RunSummary:
    relevant = [c for c in comparisons if c.business_relevant]
    generated_at = datetime.now(timezone.utc).isoformat()

    if not relevant:
        # a run with no business-relevant changes can still have genuinely
        # low-confidence extraction (e.g. a rerun that happens to match its
        # prior snapshot on an ambiguous record) - confidence must gate review
        # independent of whether a change was also detected, or uncertainty
        # silently becomes false certainty (engineering guidelines, section 7).
        return RunSummary(
            run_id=run_id,
            workflow=workflow,
            generated_at=generated_at,
            headline=f"No business-relevant changes detected for {entity_key} in this run.",
            key_changes=[],
            recommended_owner="Growth",
            confidence_note=(
                f"{low_confidence_count} row(s) had low extraction confidence."
                if low_confidence_count else "All observed records matched the prior snapshot within threshold."
            ),
            requires_human_review=low_confidence_count > 0,
        )

    try:
        from agents.llm import active_provider, call_structured

        provider = active_provider()
        changes_text = "\n".join(
            f"- {c.entity_name}: {c.change_type.value} "
            f"(prev={c.previous_value}, current={c.current_value}, delta_pct={c.delta_pct})"
            for c in relevant
        )
        user_prompt = (
            f"Workflow: {workflow}\nEntity: {entity_key}\nRun: {run_id}\n"
            f"Low-confidence extracted rows: {low_confidence_count}\n"
            f"Detected changes:\n{changes_text}"
        )
        raw = call_structured(
            COMPLETION_SYSTEM_PROMPT, user_prompt,
            node="completion", purpose=f"Summarize {len(relevant)} change(s) for {entity_key}", run_id=run_id,
            input_ref_ids={"change_ids": change_ids} if change_ids else None,
        )
        return RunSummary(
            run_id=run_id,
            workflow=workflow,
            generated_at=generated_at,
            generated_by=provider or "deterministic",
            **raw,
        )
    except Exception:
        bullets = [
            f"{c.entity_name}: {c.change_type.value} ({c.previous_value} -> {c.current_value})"
            for c in relevant
        ]
        return RunSummary(
            run_id=run_id,
            workflow=workflow,
            generated_at=generated_at,
            headline=f"{len(relevant)} business-relevant change(s) detected for {entity_key}.",
            key_changes=bullets,
            recommended_owner="Growth",
            confidence_note=(
                f"{low_confidence_count} row(s) had low extraction confidence."
                if low_confidence_count else "All rows extracted with high confidence."
            ),
            requires_human_review=low_confidence_count > 0,
        )
